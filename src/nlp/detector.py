"""
Детектор трёх типов проблем:
  - duplicate     : семантически одинаковые нормы из разных законов
  - contradiction : похожие по теме; подтверждение NLI (contradiction)
  - outdated      : семантическая близость к якорям «утрата силы / отмена»
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import faiss
import numpy as np

from src.nlp.nli_infer import contradiction_probs_for_pairs

# ─── Пороги ──────────────────────────────────────────────────────────────────
DUPLICATE_THRESHOLD = 0.90   # cosine similarity (верхняя граница для «не дубль» в паре contradiction)
CONTRADICTION_LOW = 0.85     # нижняя граница сходства кандидатов (настраивается из UI)
CONTRADICTION_FAISS_K = 100  # top-k соседей на статью для кандидатов
NLI_CONTRADICTION_THRESHOLD = 0.80
NLI_BATCH_SIZE = 4           # Меньше батч — стабильнее память (прежний был 12)

OUTDATED_ANCHOR_THRESHOLD = 0.88

OUTDATED_ANCHOR_SENTENCES = [
    "Данная норма официально отменена и утратила юридическую силу.",
    "Нормативный акт признан недействующим и не подлежит применению.",
    "Положение утратило силу в связи с принятием нового законодательства.",
    "Текст исключён из действующей редакции кодекса как утративший силу.",
]


@dataclass
class Problem:
    type: str  # duplicate | contradiction | outdated
    article_a: dict
    article_b: Optional[dict] = None
    score: float = 0.0
    nli_score: float = 0.0
    explanation: str = ""
    marker: str = ""


def _cosine_matrix(embeddings: np.ndarray) -> np.ndarray:
    vecs = embeddings.copy().astype("float32")
    faiss.normalize_L2(vecs)
    return vecs @ vecs.T


def detect_duplicates(embeddings: np.ndarray, articles: list) -> list:
    sim = _cosine_matrix(embeddings)
    problems = []
    n = len(articles)
    for i in range(n):
        for j in range(i + 1, n):
            score = float(sim[i, j])
            if score >= DUPLICATE_THRESHOLD:
                if articles[i]["doc_id"] != articles[j]["doc_id"]:
                    problems.append(
                        Problem(
                            type="duplicate",
                            article_a=articles[i],
                            article_b=articles[j],
                            score=score,
                        )
                    )
    return sorted(problems, key=lambda p: -p.score)


def _ensure_faiss_index(
    embeddings: np.ndarray, faiss_index: Optional[faiss.Index]
) -> faiss.Index:
    if faiss_index is not None:
        return faiss_index
    vecs = embeddings.copy().astype("float32")
    faiss.normalize_L2(vecs)
    d = vecs.shape[1]
    idx = faiss.IndexFlatIP(d)
    idx.add(vecs)
    return idx


def detect_contradictions(
    embeddings: np.ndarray,
    articles: list,
    faiss_index: Optional[faiss.Index] = None,
) -> list:
    n = len(articles)
    if n < 2:
        return []

    vecs = embeddings.copy().astype("float32")
    faiss.normalize_L2(vecs)
    index = _ensure_faiss_index(embeddings, faiss_index)

    upper = DUPLICATE_THRESHOLD
    k = min(CONTRADICTION_FAISS_K, n)
    pairs_seen: set[tuple[int, int]] = set()
    ordered_pairs: list[tuple[int, int, float]] = []

    for i in range(n):
        sims, idxs = index.search(vecs[i : i + 1], k)
        for sim, j in zip(sims[0], idxs[0]):
            if j < 0 or j == i:
                continue
            a, b = (i, j) if i < j else (j, i)
            if (a, b) in pairs_seen:
                continue
            if sim < CONTRADICTION_LOW or sim >= upper:
                continue
            if articles[a]["doc_id"] == articles[b]["doc_id"]:
                continue
            pairs_seen.add((a, b))
            ordered_pairs.append((a, b, float(sim)))

    if not ordered_pairs:
        return []

    text_pairs = [(articles[a]["text"], articles[b]["text"]) for a, b, _ in ordered_pairs]
    nli_scores = contradiction_probs_for_pairs(text_pairs, batch_size=NLI_BATCH_SIZE)

    problems = []
    for (a, b, score), nli in zip(ordered_pairs, nli_scores):
        if nli >= NLI_CONTRADICTION_THRESHOLD:
            problems.append(
                Problem(
                    type="contradiction",
                    article_a=articles[a],
                    article_b=articles[b],
                    score=score,
                    nli_score=nli,
                )
            )
    return sorted(problems, key=lambda p: -p.nli_score)


def detect_outdated(embeddings: np.ndarray, articles: list) -> list:
    from src.nlp.embedder import get_anchor_embedding

    anchor = get_anchor_embedding(OUTDATED_ANCHOR_SENTENCES)

    vecs = embeddings.copy().astype("float32")
    faiss.normalize_L2(vecs)
    sims = (vecs @ anchor.T).ravel()

    problems = []
    for idx, art in enumerate(articles):
        s = float(sims[idx])
        if s > OUTDATED_ANCHOR_THRESHOLD:
            problems.append(
                Problem(
                    type="outdated",
                    article_a=art,
                    score=s,
                    marker="semantic_anchor",
                    explanation=(
                        f"Высокая семантическая близость к шаблону утраты силы "
                        f"(cos={s:.3f})."
                    ),
                )
            )
    return sorted(problems, key=lambda p: -p.score)


def run_all_detectors(
    embeddings: np.ndarray,
    articles: list,
    faiss_index: Optional[faiss.Index] = None,
) -> dict:
    print("Поиск дублей...")
    dups = detect_duplicates(embeddings, articles)
    print(f"  Найдено дублей: {len(dups)}")

    print("Поиск противоречий (FAISS + NLI)...")
    cons = detect_contradictions(embeddings, articles, faiss_index=faiss_index)
    print(f"  Найдено противоречий: {len(cons)}")

    print("Поиск устаревших норм (семантический якорь)...")
    old = detect_outdated(embeddings, articles)
    print(f"  Найдено устаревших: {len(old)}")

    return {
        "duplicates": dups,
        "contradictions": cons,
        "outdated": old,
        "all": dups + cons + old,
    }
