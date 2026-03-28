"""
Трёхклассовый NLI для пар текстов: cointegrated/rubert-base-cased-nli-threeway.
Вероятность contradiction — max по двум направлениям (premise/hypothesis).
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import gc

MODEL_NAME = "cointegrated/rubert-base-cased-nli-threeway"

_tokenizer = None
_model = None


def unload_nli():
    global _tokenizer, _model
    if _model is not None:
        print("Выгружаем NLI модель из VRAM...")
        _model.cpu()
        del _model
        del _tokenizer
        _model = None
        _tokenizer = None
        torch.cuda.empty_cache()
        gc.collect()
        print("VRAM очищена (NLI).")


def _get_nli():
    global _tokenizer, _model
    if _model is not None:
        return _tokenizer, _model
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    _model.eval()
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _model.to(dev)
    return _tokenizer, _model


def contradiction_probs_for_pairs(
    pairs: list[tuple[str, str]],
    batch_size: int = 12,
    max_length: int = 512,
) -> list[float]:
    """
    Для каждой пары (text_a, text_b) возвращает max(P(contradiction|A,B), P(contradiction|B,A)).
    """
    if not pairs:
        return []
    tokenizer, model = _get_nli()
    device = next(model.parameters()).device
    cid = model.config.label2id.get("contradiction")
    if cid is None:
        raise RuntimeError("NLI: в конфиге модели нет метки contradiction")

    out: list[float] = []
    for start in range(0, len(pairs), batch_size):
        chunk = pairs[start : start + batch_size]
        prems_a = [p[0] for p in chunk]
        hyps_b = [p[1] for p in chunk]
        enc1 = tokenizer(
            prems_a,
            hyps_b,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        enc2 = tokenizer(
            hyps_b,
            prems_a,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        enc1 = {k: v.to(device) for k, v in enc1.items()}
        enc2 = {k: v.to(device) for k, v in enc2.items()}
        with torch.no_grad():
            logits1 = model(**enc1).logits
            logits2 = model(**enc2).logits
            p1 = F.softmax(logits1, dim=-1)[:, cid]
            p2 = F.softmax(logits2, dim=-1)[:, cid]
        for i in range(len(chunk)):
            out.append(float(max(p1[i].item(), p2[i].item())))
    return out
