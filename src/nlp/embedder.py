"""
BGE-M3 embeddings + FAISS (in-memory ANN) + ChromaDB (персистентные векторы на диске).

Эмбеддинги и метаданные id/doc_id хранятся в Chroma (data/cache/chroma); список статей — в pickle.
FAISS IndexFlatIP собирается в RAM при load для текущего детектора (cosine через L2-norm + IP).
Полная матрица дублей O(n^2) по-прежнему ограничена размером корпуса в памяти.
"""
import json
import os
import pickle
from pathlib import Path

import faiss
import numpy as np
from tqdm import tqdm

# ── Compatibility patch ──────────────────────────────────────────────────────
# transformers 5.x renamed is_flash_attn_greater_or_equal_2_10 → is_flash_attn_greater_or_equal
# FlagEmbedding 1.x still tries to import the old name; patch it before the import.
try:
    import transformers.utils as _tu
    if not hasattr(_tu, "is_flash_attn_greater_or_equal_2_10"):
        _tu.is_flash_attn_greater_or_equal_2_10 = getattr(
            _tu, "is_flash_attn_greater_or_equal", lambda: False
        )
except Exception:
    pass
# ───────────────────────────────────────────────────────────────────────────────

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR = CACHE_DIR / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

_model = None
_model_type = None  # 'bge' | 'sbert'
_chunk_splitter = None

import torch
import gc

def unload_model():
    global _model
    if _model is not None:
        print("Выгружаем BGE-M3 из VRAM...")
        try:
            if hasattr(_model, 'model'):
                _model.model.cpu()
        except: pass
        del _model
        _model = None
        torch.cuda.empty_cache()
        gc.collect()
        print("VRAM очищена.")


def _get_recursive_splitter():
    global _chunk_splitter
    if _chunk_splitter is None:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        _chunk_splitter = RecursiveCharacterTextSplitter(
            chunk_size=3000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    return _chunk_splitter

def get_model():
    global _model, _model_type
    if _model is not None:
        return _model

    has_gpu = torch.cuda.is_available()

    # ── Try FlagEmbedding / BGE-M3 first ────────────────────────────────────
    if has_gpu:
        try:
            print("GPU обнаружен. Загружаем BGE-M3 (первый раз ~2-3 мин)...")
            from FlagEmbedding import BGEM3FlagModel
            _model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
            _model_type = "bge"
            print("Модель BGE-M3 загружена.")
            return _model
        except Exception as e:
            print(f"BGE-M3 недоступна: {e}")
    else:
        print("GPU не обнаружен (установлена CPU-версия PyTorch).")
        print("Пропускаем тяжелую модель BGE-M3 во избежание зависаний...")

    # ── Fallback: sentence-transformers (multilingual) ────────────────────────
    try:
        print("Загружаем легкую модель (paraphrase-multilingual-MiniLM-L12...) для CPU...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        _model_type = "sbert"
        print("Легкая модель загружена.")
        return _model
    except Exception as e:
        print(f"sentence-transformers недоступны: {e}")

    raise RuntimeError("Ни BGE-M3, ни sentence-transformers не удалось загрузить. См. README.")


def _resolve_embed_batch_size(batch_size: int | None) -> int:
    if isinstance(batch_size, int) and batch_size > 0:
        return batch_size
    env_bs = os.environ.get("EMBED_BATCH_SIZE")
    if env_bs:
        try:
            parsed = int(env_bs)
            if parsed > 0:
                return parsed
        except Exception:
            pass
    return 16 if torch.cuda.is_available() else 8


def embed_texts(texts: list, batch_size: int | None = None, show_progress: bool = True) -> np.ndarray:
    batch_size = _resolve_embed_batch_size(batch_size)
    model = get_model()
    if _model_type == "bge":
        # BGEM3FlagModel.encode не поддерживает show_progress_bar и выдает TypeError
        out = model.encode(
            texts, 
            batch_size=batch_size, 
            max_length=512, 
            return_dense=True
        )
        return out["dense_vecs"].astype("float32")
    else:
        # sentence_transformers path
        return model.encode(
            texts, 
            batch_size=batch_size, 
            show_progress_bar=show_progress
        ).astype("float32")


def get_anchor_embedding(anchors: list) -> np.ndarray:
    """Возвращает усредненный вектор якорных фраз (из кэша или считает)."""
    cache_path = CACHE_DIR / "outdated_anchors.npy"
    if cache_path.exists():
        return np.load(cache_path)
    
    print("Генерируем кэш для семантических якорей...")
    vecs = embed_texts(anchors, batch_size=len(anchors), show_progress=False)
    anchor = vecs.mean(axis=0).astype("float32").reshape(1, -1)
    faiss.normalize_L2(anchor)
    np.save(cache_path, anchor)
    return anchor


def build_index(embeddings: np.ndarray) -> faiss.Index:
    vecs = embeddings.copy()
    faiss.normalize_L2(vecs)
    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)
    return index


def _chroma_collection_name(prefix: str) -> str:
    return f"legal_entropy_{prefix}"


def _get_chroma_collection(prefix: str):
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=_chroma_collection_name(prefix),
        metadata={"hnsw:space": "cosine"},
    )


def _save_chroma(embeddings: np.ndarray, articles: list, prefix: str) -> None:
    try:
        coll = _get_chroma_collection(prefix)
        ids = [str(a["id"]) for a in articles]
        vecs = np.asarray(embeddings, dtype="float32")
        emb_list = [vecs[i].tolist() for i in range(len(articles))]
        metadatas = [{"doc_id": str(a.get("doc_id", ""))} for a in articles]
        coll.upsert(ids=ids, embeddings=emb_list, metadatas=metadatas)
    except Exception as e:
        print(f"Предупреждение: ChromaDB не сохранена ({e}). Доступны npy + FAISS.")


def _load_chroma_embeddings(articles: list, prefix: str) -> np.ndarray | None:
    try:
        coll = _get_chroma_collection(prefix)
        ids = [str(a["id"]) for a in articles]
        if not ids:
            return np.zeros((0, 1), dtype="float32")
        res = coll.get(ids=ids, include=["embeddings"])
        got = res.get("embeddings")
        if not got or len(got) != len(articles):
            return None
        for row in got:
            if row is None:
                return None
        return np.array(got, dtype="float32")
    except Exception:
        return None


def save_embeddings(embeddings: np.ndarray, articles: list, prefix: str = "main"):
    np.save(CACHE_DIR / f"{prefix}_embeddings.npy", embeddings)
    with open(CACHE_DIR / f"{prefix}_articles.pkl", "wb") as f:
        pickle.dump(articles, f)
    faiss.write_index(build_index(embeddings), str(CACHE_DIR / f"{prefix}.index"))
    _save_chroma(embeddings, articles, prefix)
    print(f"Сохранено: {len(articles)} статей, {embeddings.shape} (npy + FAISS; Chroma при успешном импорте)")


def load_embeddings(prefix: str = "main"):
    pkl_path = CACHE_DIR / f"{prefix}_articles.pkl"
    with open(pkl_path, "rb") as f:
        articles = pickle.load(f)
    emb_chroma = _load_chroma_embeddings(articles, prefix)
    npy_path = CACHE_DIR / f"{prefix}_embeddings.npy"
    if emb_chroma is not None and emb_chroma.shape[0] == len(articles):
        embeddings = emb_chroma
    elif npy_path.exists():
        embeddings = np.load(npy_path)
    else:
        raise FileNotFoundError(
            f"Нет векторов: ни Chroma, ни {npy_path}. Запустите embedder или save_embeddings."
        )
    if len(embeddings) != len(articles):
        raise ValueError("Число эмбеддингов не совпадает со списком статей")

    idx_path = CACHE_DIR / f"{prefix}.index"
    if emb_chroma is None and idx_path.exists():
        index = faiss.read_index(str(idx_path))
    else:
        index = build_index(embeddings)
    return embeddings, articles, index


def prepare_articles(documents: list) -> tuple:
    """Из списка документов — плоский список статей (с чанкингом) + тексты для embedding."""
    all_articles = []
    
    def chunk_text(text: str, max_chars_soft: int = 2800) -> list:
        if not text:
            return []
        if len(text) <= max_chars_soft:
            return [text]
        splitter = _get_recursive_splitter()
        parts = splitter.split_text(text)
        return parts if parts else [text]

    for doc in documents:
        if not isinstance(doc, dict):
            continue
            
        articles_list = doc.get("articles", [])
        doc_title = doc.get("title", "Неизвестный НПА")
        doc_url = doc.get("url", "")
        
        for art in articles_list:
            if not art.get("text"):
                continue
                
            chunks = chunk_text(art["text"])
            for idx, chunk in enumerate(chunks):
                art_copy = art.copy()
                if len(chunks) > 1:
                    art_copy["id"] = f"{art['id']}_chunk_{idx}"
                
                art_copy["text"] = chunk
                art_copy["doc_title"] = doc_title
                art_copy["doc_url"] = doc_url
                all_articles.append(art_copy)
                    
    texts = [a["text"] for a in all_articles]
    return all_articles, texts


if __name__ == "__main__":
    import glob, json
    docs = []
    for p in glob.glob("data/parsed/*.json"):
        with open(p, encoding="utf-8") as f:
            docs.append(json.load(f))

    if not docs:
        print("Нет документов в data/parsed/. Сначала запусти парсер.")
    else:
        articles, texts = prepare_articles(docs)
        print(f"Всего статей: {len(texts)}")
        embeddings = embed_texts(texts)
        save_embeddings(embeddings, articles)
        print("Готово!")
