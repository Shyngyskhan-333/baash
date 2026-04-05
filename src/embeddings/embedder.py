
import functools
from pathlib import Path
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
MODEL_CACHE_DIR = Path("data/models")
_model = None
_model_error = None

def get_model() -> SentenceTransformer:
    global _model, _model_error
    if _model_error is not None:
        raise RuntimeError(_model_error)
    if _model is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

        print(f"Загрузка модели {MODEL_NAME} на {device}...")
        MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:

            _model = SentenceTransformer(
                MODEL_NAME,
                device=device,
                cache_folder=str(MODEL_CACHE_DIR),
                local_files_only=True,
            )
        except Exception:

            print(f"[EMBEDDER] Модель не найдена локально, скачиваем с HuggingFace...")
            try:
                _model = SentenceTransformer(
                    MODEL_NAME,
                    device=device,
                    cache_folder=str(MODEL_CACHE_DIR),
                    local_files_only=False,
                )
                print(f"[EMBEDDER] Модель скачана и сохранена в {MODEL_CACHE_DIR}")
            except Exception as error:
                _model_error = str(error)
                raise
    return _model

@functools.lru_cache(maxsize=10000)
def _embed_text_cached(text: str, is_query: bool = False) -> np.ndarray:

    if not text.strip():
        return np.zeros(384, dtype=np.float16)

    prefix = "query: " if is_query else "passage: "
    vec = get_model().encode(prefix + text, normalize_embeddings=True)
    result = vec.astype(np.float16)
    result.flags.writeable = False
    return result

def embed_text(text: str, is_query: bool = False) -> np.ndarray:

    return _embed_text_cached(text, is_query).copy()

def embed_texts(texts: list[str], is_query: bool = False, batch_size: int = 32) -> np.ndarray:

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