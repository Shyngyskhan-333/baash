"""
Сравнение редакций НПА: сопоставление статей по номеру и косинус эмбеддингов.
"""
from __future__ import annotations

import re
from collections import defaultdict

import faiss
import numpy as np

from src.nlp.embedder import embed_texts

ARTICLE_NUM_RE = re.compile(r"Статья\s*(\d+)", re.IGNORECASE | re.UNICODE)

# Пороги (план): float 1.0 недостижим — «без изменений» ~0.995+, смысловое < 0.95 → LLM
VERSION_UNCHANGED_MIN = 0.995
VERSION_SEMANTIC_CHANGE_MAX = 0.95

MAX_TEXT_CHARS = 8000


def extract_article_number(art: dict) -> int | None:
    for src in (art.get("number") or "", (art.get("text") or "")[:500]):
        m = ARTICLE_NUM_RE.search(src)
        if m:
            return int(m.group(1))
    return None


def merge_chunked_articles(articles: list) -> list:
    """Объединяет чанки с id вида base_chunk_N в одну статью."""
    groups: dict[str, list] = defaultdict(list)
    for a in articles:
        aid = a.get("id") or ""
        base = aid.split("_chunk_")[0]
        groups[base].append(a)
    merged = []
    for base, parts in groups.items():
        parts.sort(key=lambda x: x.get("id", ""))
        text = "\n\n".join((p.get("text") or "").strip() for p in parts if p.get("text"))
        first = parts[0].copy()
        first["text"] = text
        first["id"] = base
        merged.append(first)
    return merged


def pair_articles_by_number(
    articles_old: list,
    articles_new: list,
) -> tuple[list[tuple[dict, dict]], list[dict], list[dict]]:
    old_by_n: dict[int, dict] = {}
    for a in articles_old:
        n = extract_article_number(a)
        if n is not None:
            old_by_n[n] = a
    new_by_n: dict[int, dict] = {}
    for a in articles_new:
        n = extract_article_number(a)
        if n is not None:
            new_by_n[n] = a
    common = sorted(set(old_by_n) & set(new_by_n))
    pairs = [(old_by_n[n], new_by_n[n]) for n in common]
    only_old = [old_by_n[n] for n in sorted(set(old_by_n) - set(new_by_n))]
    only_new = [new_by_n[n] for n in sorted(set(new_by_n) - set(old_by_n))]
    return pairs, only_old, only_new


def embedding_cosine_similarity(text_a: str, text_b: str) -> float:
    a = (text_a or "")[:MAX_TEXT_CHARS]
    b = (text_b or "")[:MAX_TEXT_CHARS]
    vecs = embed_texts([a, b], batch_size=2)
    v = vecs.astype("float32").copy()
    faiss.normalize_L2(v)
    return float(np.dot(v[0], v[1]))


def _prepare_articles_list(doc: dict, merge_chunks: bool) -> list:
    raw = doc.get("articles") or []
    return merge_chunked_articles(raw) if merge_chunks else list(raw)


def compare_document_versions(
    doc_old: dict,
    doc_new: dict,
    merge_chunks: bool = True,
) -> list[dict]:
    """
    Пары статей с номером + cosine. Каждый элемент:
    article_num, score, article_old, article_new, label ('unchanged'|'minor'|'semantic').
    """
    summary = full_version_compare(doc_old, doc_new, merge_chunks=merge_chunks)
    return summary["pairs_detail"]


def full_version_compare(
    doc_old: dict,
    doc_new: dict,
    merge_chunks: bool = True,
) -> dict:
    """Полный отчёт: пары со score, только в старой / только в новой."""
    ao = _prepare_articles_list(doc_old, merge_chunks)
    an = _prepare_articles_list(doc_new, merge_chunks)
    pairs, only_old, only_new = pair_articles_by_number(ao, an)
    if not pairs:
        return {
            "pairs_detail": [],
            "only_old": only_old,
            "only_new": only_new,
            "paired_count": 0,
        }

    olds = [(o.get("text") or "")[:MAX_TEXT_CHARS] for o, _ in pairs]
    news = [(n.get("text") or "")[:MAX_TEXT_CHARS] for _, n in pairs]
    emb = embed_texts(olds + news, batch_size=8)
    n_p = len(pairs)
    o_mat = emb[:n_p].astype("float32").copy()
    n_mat = emb[n_p:].astype("float32").copy()
    faiss.normalize_L2(o_mat)
    faiss.normalize_L2(n_mat)

    pairs_detail = []
    for i, (art_o, art_n) in enumerate(pairs):
        score = float(np.dot(o_mat[i], n_mat[i]))
        num = extract_article_number(art_o) or extract_article_number(art_n) or -1
        if score >= VERSION_UNCHANGED_MIN:
            label = "unchanged"
        elif score < VERSION_SEMANTIC_CHANGE_MAX:
            label = "semantic"
        else:
            label = "minor"
        pairs_detail.append(
            {
                "article_num": num,
                "score": score,
                "article_old": art_o,
                "article_new": art_n,
                "label": label,
            }
        )
    pairs_detail.sort(key=lambda x: x["article_num"])
    return {
        "pairs_detail": pairs_detail,
        "only_old": only_old,
        "only_new": only_new,
        "paired_count": len(pairs_detail),
    }


def version_compare_summary(doc_old: dict, doc_new: dict) -> dict:
    """Обёртка с merge_chunks=True по умолчанию (как в плане)."""
    return full_version_compare(doc_old, doc_new, merge_chunks=True)
