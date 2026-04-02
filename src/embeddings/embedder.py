"""
CPU-оптимизированный модуль векторизации.
Использует intfloat/multilingual-e5-small (очень быстрая и точная).
"""
import functools
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
            
        print(f"Загрузка модели {MODEL_NAME} на {device}...")
        _model = SentenceTransformer(MODEL_NAME, device=device)
    return _model

@functools.lru_cache(maxsize=10000)
def embed_text(text: str, is_query: bool = False) -> np.ndarray:
    """Одиночный эмбеддинг с LRU кэшированием (мгновенно для повторяющихся запросов)."""
    if not text.strip():
        return np.zeros(384, dtype=np.float16)
        
    prefix = "query: " if is_query else "passage: "
    vec = get_model().encode(prefix + text, normalize_embeddings=True)
    return vec.astype(np.float16)

def embed_texts(texts: list[str], is_query: bool = False, batch_size: int = 32) -> np.ndarray:
    """Батчевая векторизация (сохраняет float16 для экономии ОЗУ)."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float16)
        
    prefix = "query: " if is_query else "passage: "
    prefixed_texts = [prefix + t for t in texts]
    
    vecs = get_model().encode(
        prefixed_texts, 
        batch_size=batch_size, 
        normalize_embeddings=True, 
        show_progress_bar=True
    )
    return vecs.astype(np.float16)
