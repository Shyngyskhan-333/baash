"""
Гибридный полнотекстовый + семантический поиск: BM25 + FAISS (IndexHNSWFlat).
Реализует паттерн Reciprocal Rank Fusion (RRF) для слияния результатов.
Идеально работает на CPU. Умное инкрементальное хранение на диск.
"""
import pickle
import re
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from src.embeddings.embedder import embed_text, embed_texts


class LegalRetriever:
    def __init__(self, data_dir: str = "data"):
        self.faiss_dir = Path(data_dir) / "faiss"
        self.faiss_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_dir = Path(data_dir) / "embeddings"
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        
        self.faiss_path = self.faiss_dir / "faiss.index"
        self.bm25_path = self.faiss_dir / "bm25.pkl"
        self.meta_path = self.embeddings_dir / "metadata.pkl"
        
        self.dim = 384  # для e5-small
        self.index = None
        self.bm25 = None
        self.metadata = []  # Список словарей с чанками
        
        self.load()

    def _tokenize(self, text: str) -> list[str]:
        text = text.lower()
        return re.findall(r"(?u)\b\w+\b", text)

    def load(self):
        """Загружает индексы из диска в RAM, если существуют."""
        if self.faiss_path.exists():
            self.index = faiss.read_index(str(self.faiss_path))
        else:
            self.index = faiss.IndexHNSWFlat(self.dim, 32, faiss.METRIC_INNER_PRODUCT)
        
        if self.meta_path.exists():
            with open(self.meta_path, "rb") as f:
                self.metadata = pickle.load(f)
                
        if self.bm25_path.exists():
            with open(self.bm25_path, "rb") as f:
                self.bm25 = pickle.load(f)

    def save(self):
        """Сохраняем всё на диск (никаких пересчетов при рестарте)."""
        faiss.write_index(self.index, str(self.faiss_path))
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        if self.bm25 is not None:
            with open(self.bm25_path, "wb") as f:
                pickle.dump(self.bm25, f)
                
    def add_documents(self, documents: list[dict]) -> int:
        """
        Добавляет новые документы в индекс инкрементально. 
        documents: JSON-структура от adilet_scraper.py
        """
        existing_doc_ids = {m["doc_id"] for m in self.metadata}
        
        new_chunks = []
        for doc in documents:
            if doc["doc_id"] in existing_doc_ids:
                continue
            for art in doc.get("articles", []):
                for chunk in art.get("chunks", []):
                    new_chunks.append({
                        "doc_id": doc["doc_id"],
                        "doc_title": doc["title"],
                        "article_number": art["article_number"],
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "hierarchy": chunk["hierarchy"]
                    })
                    
        if not new_chunks:
            return 0
            
        print(f"Векторизация {len(new_chunks)} новых логических чанков (e5-small)...")
        texts = [c["text"] for c in new_chunks]
        
        vecs_fp16 = embed_texts(texts, is_query=False, batch_size=32)
        
        vecs_fp32 = vecs_fp16.astype(np.float32)
        faiss.normalize_L2(vecs_fp32)
        
        self.index.add(vecs_fp32)
        self.metadata.extend(new_chunks)
        
        print("Обновление BM25 индекса...")
        all_texts = [m["text"] for m in self.metadata]
        tokenized_corpus = [self._tokenize(t) for t in all_texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        self.save()
        return len(new_chunks)

    def search_hybrid(self, query: str, top_k: int = 10) -> list[dict]:
        """
        BM25 (top-30) + FAISS (top-30) -> объединение через Reciprocal Rank Fusion (RRF).
        Возвращает top_k релевантных чанков.
        """
        if not self.metadata or len(self.metadata) == 0:
            return []
            
        search_k = min(30, len(self.metadata))
        
        query_vec = embed_text(query, is_query=True)
        query_vec_fp32 = query_vec.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(query_vec_fp32)
        
        faiss_scores, faiss_indices = self.index.search(query_vec_fp32, search_k)
        
        tokenized_query = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_indices = np.argsort(bm25_scores)[::-1][:search_k]
        
        rrf_k = 60
        rrf_scores = {}
        
        for rank, idx in enumerate(faiss_indices[0]):
            idx = int(idx) # Избегаем numpy integer types в dict keys
            if idx == -1: 
                continue
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
            
        for rank, idx in enumerate(bm25_indices):
            idx = int(idx)
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
            
        sorted_indices = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_k]
        
        results = []
        for idx in sorted_indices:
            fa_score = 0.0
            fs_loc = np.where(faiss_indices[0] == idx)[0]
            if len(fs_loc) > 0:
                fa_score = float(faiss_scores[0][fs_loc[0]])
                
            item = self.metadata[idx].copy()
            item["rrf_score"] = rrf_scores[idx]
            item["cosine_score"] = fa_score
            item["bm25_score"] = bm25_scores[idx]
            results.append(item)
            
        return results

    def rebuild_index(self) -> int:
        """Очищает индексы и BM25, затем считывает чистые JSON-файлы из PARSED_DIR."""
        import json
        
        print("Очистка существующих векторных баз из RAM и SSD (FAISS/BM25)...")
        self.metadata = []
        self.index = faiss.IndexHNSWFlat(self.dim, 32, faiss.METRIC_INNER_PRODUCT)
        self.bm25 = None
        
        if self.faiss_path.exists():
            self.faiss_path.unlink()
        if self.meta_path.exists():
            self.meta_path.unlink()
        if self.bm25_path.exists():
            self.bm25_path.unlink()
            
        print("Считывание пересобранных (Дедублицированных) JSON из data/parsed/...")
        parsed_dir = Path("data/parsed")
        
        docs_to_add = []
        for file_path in parsed_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    docs_to_add.append(json.load(f))
                except json.JSONDecodeError:
                    pass
                    
        added = self.add_documents(docs_to_add)
        print(f"Индекс FAISS пересобран! Итоговая емкость: {len(self.metadata)} логических кусков.")
        return added
