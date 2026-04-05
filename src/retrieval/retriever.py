
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

        self.dim = 384
        self.index = None
        self.bm25 = None
        self.metadata = []

        self.load()

    def _tokenize(self, text: str) -> list:
        return re.findall(r"(?u)\b\w+\b", text.lower())

    def load(self):

        if self.faiss_path.exists():
            self.index = faiss.read_index(str(self.faiss_path))
        else:
            self.index = faiss.IndexFlatIP(self.dim)

        if self.meta_path.exists():
            try:
                with open(self.meta_path, "rb") as f:
                    self.metadata = pickle.load(f)
            except Exception:
                self.metadata = []

        if self.bm25_path.exists():
            try:
                with open(self.bm25_path, "rb") as f:
                    self.bm25 = pickle.load(f)
            except Exception:
                self.bm25 = None

    def save(self):

        faiss.write_index(self.index, str(self.faiss_path))
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        if self.bm25 is not None:
            with open(self.bm25_path, "wb") as f:
                pickle.dump(self.bm25, f)

    def add_documents(self, documents: list) -> int:

        existing_doc_ids = {m["doc_id"] for m in self.metadata}

        new_chunks = []
        for doc in documents:
            if doc.get("doc_id") in existing_doc_ids:
                continue
            for art in doc.get("articles", []):
                for chunk in art.get("chunks", []):
                    new_chunks.append({
                        "doc_id": doc["doc_id"],
                        "doc_title": doc.get("title", doc["doc_id"]),
                        "article_number": art.get("article_number", ""),
                        "chunk_id": chunk.get("chunk_id", f'{doc["doc_id"]}_{len(new_chunks)}'),
                        "text": chunk.get("text", ""),
                        "hierarchy": chunk.get("hierarchy", []),
                    })

        if not new_chunks:
            return 0

        new_chunks = [c for c in new_chunks if c["text"].strip()]
        if not new_chunks:
            return 0

        print(f"Векторизация {len(new_chunks)} новых чанков (e5-small)...")
        texts = [c["text"] for c in new_chunks]
        vecs_fp32 = embed_texts(texts, is_query=False, batch_size=32).astype(np.float32)
        faiss.normalize_L2(vecs_fp32)

        self.index.add(vecs_fp32)
        self.metadata.extend(new_chunks)

        print("Обновление BM25 индекса...")
        all_texts = [m["text"] for m in self.metadata]
        self.bm25 = BM25Okapi([self._tokenize(t) for t in all_texts])

        self.save()
        return len(new_chunks)

    def search_hybrid(self, query: str, top_k: int = 10, doc_ids: list = None) -> list:

        if not self.metadata:
            return []

        search_k = min(150, len(self.metadata)) if doc_ids else min(30, len(self.metadata))
        rrf_k = 60
        rrf_scores: dict = {}

        faiss_scores = np.empty((1, 0), dtype=np.float32)
        faiss_indices = np.empty((1, 0), dtype=np.int64)
        try:
            query_vec = embed_text(query, is_query=True).astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(query_vec)
            faiss_scores, faiss_indices = self.index.search(query_vec, search_k)

            for rank, idx in enumerate(faiss_indices[0]):
                if idx == -1:
                    continue
                if doc_ids and self.metadata[int(idx)].get("doc_id") not in doc_ids:
                    continue
                rrf_scores[int(idx)] = rrf_scores.get(int(idx), 0.0) + 1.0 / (rrf_k + rank + 1)
        except Exception as error:
            print(f"[RETRIEVER] Semantic search unavailable, falling back to BM25 only: {error}")

        if self.bm25 is not None:
            tokenized_query = self._tokenize(query)
            bm25_raw = self.bm25.get_scores(tokenized_query)
            bm25_indices = np.argsort(bm25_raw)[::-1][:search_k]
            for rank, idx in enumerate(bm25_indices):
                if doc_ids and self.metadata[int(idx)].get("doc_id") not in doc_ids:
                    continue
                rrf_scores[int(idx)] = rrf_scores.get(int(idx), 0.0) + 1.0 / (rrf_k + rank + 1)

        sorted_indices = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:top_k]

        bm25_all_scores = self.bm25.get_scores(self._tokenize(query)) if self.bm25 else None

        results = []
        for idx in sorted_indices:
            fa_score = 0.0
            loc = np.where(faiss_indices[0] == idx)[0]
            if len(loc) > 0:
                fa_score = float(faiss_scores[0][loc[0]])

            item = self.metadata[idx].copy()
            item["rrf_score"] = round(rrf_scores[idx], 6)
            item["cosine_score"] = round(fa_score, 4)
            item["bm25_score"] = round(float(bm25_all_scores[idx]) if bm25_all_scores is not None else 0.0, 4)
            results.append(item)

        return results

    def search_within_document(self, doc_id: str, query: str, top_k: int = 10) -> list:

        if not self.metadata:
            return []

        doc_indices = [i for i, m in enumerate(self.metadata) if m.get("doc_id") == doc_id]
        if not doc_indices:
            return []

        query_vec = embed_text(query, is_query=True).astype(np.float32).reshape(1, -1)
        results = []
        try:
            faiss.normalize_L2(query_vec)

            search_k = min(len(self.metadata), max(top_k * 20, len(doc_indices) + 50))
            faiss_scores, faiss_indices = self.index.search(query_vec, search_k)

            for rank, idx in enumerate(faiss_indices[0]):
                if idx == -1:
                    continue
                idx = int(idx)
                if self.metadata[idx].get("doc_id") == doc_id:
                    item = self.metadata[idx].copy()
                    item["cosine_score"] = round(float(faiss_scores[0][rank]), 4)
                    results.append(item)
                    if len(results) >= top_k:
                        break
        except Exception:
            query_tokens = self._tokenize(query)
            local_items = [self.metadata[index] for index in doc_indices]
            local_bm25 = BM25Okapi([self._tokenize(item["text"]) for item in local_items])
            scores = local_bm25.get_scores(query_tokens)
            sorted_indices = np.argsort(scores)[::-1][:top_k]
            for idx in sorted_indices:
                item = local_items[int(idx)].copy()
                item["cosine_score"] = 0.0
                results.append(item)

        return results

    def rebuild_index(self) -> int:

        import json

        parsed_dir = Path("data/parsed")
        docs_to_add = []
        for file_path in parsed_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    docs_to_add.append(json.load(f))
            except Exception:
                pass

        new_chunks = []
        for doc in docs_to_add:
            for art in doc.get("articles", []):
                for chunk in art.get("chunks", []):
                    text = chunk.get("text", "")
                    if not text.strip():
                        continue
                    new_chunks.append({
                        "doc_id": doc["doc_id"],
                        "doc_title": doc.get("title", doc["doc_id"]),
                        "article_number": art.get("article_number", ""),
                        "chunk_id": chunk.get("chunk_id", f'{doc["doc_id"]}_{len(new_chunks)}'),
                        "text": text,
                        "hierarchy": chunk.get("hierarchy", []),
                    })

        if not new_chunks:
            self.metadata = []
            self.index = faiss.IndexHNSWFlat(self.dim, 32, faiss.METRIC_INNER_PRODUCT)
            self.bm25 = None
            self.save()
            return 0

        print("Пересборка индекса из подготовленных JSON...")
        texts = [chunk["text"] for chunk in new_chunks]
        vecs_fp32 = embed_texts(texts, is_query=False, batch_size=32).astype(np.float32)
        faiss.normalize_L2(vecs_fp32)

        new_index = faiss.IndexHNSWFlat(self.dim, 32, faiss.METRIC_INNER_PRODUCT)
        new_index.add(vecs_fp32)
        new_bm25 = BM25Okapi([self._tokenize(text) for text in texts])

        self.metadata = new_chunks
        self.index = new_index
        self.bm25 = new_bm25
        self.save()
        print(f"Индекс пересобран: {len(self.metadata)} чанков.")
        return len(new_chunks)