
from dataclasses import dataclass
from typing import List, Optional
import asyncio

from src.reasoning.explainer import explain_contradiction
from src.retrieval.retriever import LegalRetriever

@dataclass
class Problem:
    type: str
    chunk_a: dict
    chunk_b: dict
    scores: dict
    explanation: Optional[dict] = None

async def detect_all_problems(retriever: LegalRetriever, top_k_explain: int = 10, doc_ids: Optional[List[str]] = None, ai_caller=None) -> List[Problem]:

    if not retriever.metadata:
        return []

    problems = []

    outdated_anchor = (
        "Данная норма официально отменена и утратила юридическую силу. "
        "Нормативный акт признан недействующим и не подлежит применению. "
        "Положение утратило силу в связи с принятием нового законодательства. "
        "Текст исключён из действующей редакции кодекса как утративший силу."
    )

    OUTDATED_TOP_K = 10
    OUTDATED_COSINE = 0.92

    REPEAL_MARKERS = (
        "утратил", "утратила", "утратило", "утратили", "утрате силы", "утратой силы",
        "не действует", "недействующ", "без силы", "отменён", "отменен", "отмена",
        "исключён", "исключен", "исключена", "признан недействующим", "признана недействующей",
        "утратил силу", "утратила силу",
    )
    outdated_candidates = retriever.search_hybrid(outdated_anchor, top_k=OUTDATED_TOP_K, doc_ids=doc_ids)
    for match in outdated_candidates:
        if match.get("cosine_score", 0.0) <= OUTDATED_COSINE:
            continue
        text_lower = (match.get("text") or "").lower()
        if not any(m in text_lower for m in REPEAL_MARKERS):
            continue
        problems.append(Problem(
            type="outdated",
            chunk_a=match,
            chunk_b=match,
            scores={"cosine": match.get("cosine_score"), "nli_confidence": 1.0},
            explanation={
                "verdict": "Фрагмент содержит формулировки об утрате силы и семантически близок к эталонному шаблону repealed.",
                "markers_matched": [m for m in REPEAL_MARKERS if m in text_lower][:5],
            },
        ))

    print("[DETECTOR] Извлечение векторов из индекса...")

    ntotal = retriever.index.ntotal
    if ntotal == 0:
        return problems

    vecs_fp32 = retriever.index.reconstruct_n(0, ntotal)

    FAISS_TOP_K = 10
    COSINE_THRESHOLD = 0.90
    MAX_PAIRS_PER_ANCHOR = 3
    MAX_TOTAL_PAIRS = 400
    MIN_NLI_CONF = 0.85
    DUPLICATE_COS = 0.985
    MAX_RESULTS_PER_TYPE = 120
    MAX_PER_RELATED_DOC = 3

    faiss_scores, faiss_indices = retriever.index.search(vecs_fp32, FAISS_TOP_K)

    pairs_to_check = []
    pair_metadata = []
    seen_pairs = set()

    for i in range(len(faiss_scores)):
        row_scores = faiss_scores[i]
        row_indices = faiss_indices[i]
        row_candidates = []
        anchor_chunk = retriever.metadata[i]
        for score, j in zip(row_scores, row_indices):
            j = int(j)
            if j < 0 or j == i:
                continue
            if float(score) < COSINE_THRESHOLD:
                continue

            match = retriever.metadata[j]
            if doc_ids:
                if anchor_chunk["doc_id"] not in doc_ids or match["doc_id"] not in doc_ids:
                    continue
            if match["doc_id"] == anchor_chunk["doc_id"]:
                continue

            p_id = tuple(sorted([anchor_chunk["chunk_id"], match["chunk_id"]]))
            if p_id in seen_pairs:
                continue
            row_candidates.append((float(score), anchor_chunk, match, p_id))

        if not row_candidates:
            continue
        row_candidates.sort(key=lambda x: x[0], reverse=True)
        for score, anchor_chunk, match, p_id in row_candidates[:MAX_PAIRS_PER_ANCHOR]:
            if p_id in seen_pairs:
                continue
            seen_pairs.add(p_id)
            pairs_to_check.append((anchor_chunk["text"], match["text"], anchor_chunk["chunk_id"], match["chunk_id"]))
            pair_metadata.append((anchor_chunk, match, score))
            if len(pairs_to_check) >= MAX_TOTAL_PAIRS:
                break
        if len(pairs_to_check) >= MAX_TOTAL_PAIRS:
            break

    if not pairs_to_check:
        return problems

    try:
        from src.reasoning.nli import check_contradictions_batch
    except ImportError as exc:
        raise RuntimeError("NLI dependencies are required for contradiction detection; install requirements.txt") from exc

    nli_results = await asyncio.to_thread(check_contradictions_batch, pairs_to_check, 32)

    scored_pairs = []
    for idx, nli_res in enumerate(nli_results):
        anchor_chunk, match, cos_score = pair_metadata[idx]
        scored_pairs.append({
            "anchor": anchor_chunk,
            "match": match,
            "cos_score": cos_score,
            "nli_label": nli_res["label"],
            "nli_conf": nli_res["confidence"]
        })

    scored_pairs.sort(key=lambda x: (x["nli_label"] == "contradiction", x["nli_conf"]), reverse=True)

    explained_count = 0

    counts_by_type = {"contradiction": 0, "duplicate": 0, "outdated": 0}
    per_related = {}
    for item in scored_pairs:
        label = item["nli_label"]
        conf = item["nli_conf"]
        cos_score = item["cos_score"]

        explanation = None
        if label == "contradiction" and conf >= MIN_NLI_CONF and cos_score >= COSINE_THRESHOLD:
            related_id = item["match"].get("doc_id")
            per_key = ("contradiction", related_id)
            if counts_by_type["contradiction"] >= MAX_RESULTS_PER_TYPE:
                continue
            if related_id and per_related.get(per_key, 0) >= MAX_PER_RELATED_DOC:
                continue
            if explained_count < top_k_explain and ai_caller:
                explanation = await explain_contradiction(
                    text_a=item["anchor"]["text"],
                    text_b=item["match"]["text"],
                    law_a=item["anchor"]["doc_title"],
                    law_b=item["match"]["doc_title"],
                    ai_caller=ai_caller
                )
                explained_count += 1

            problems.append(Problem(
                type="contradiction",
                chunk_a=item["anchor"],
                chunk_b=item["match"],
                scores={"cosine": cos_score, "nli_confidence": conf},
                explanation=explanation
            ))
            counts_by_type["contradiction"] += 1
            if related_id:
                per_related[per_key] = per_related.get(per_key, 0) + 1

        elif cos_score >= DUPLICATE_COS and label in ["entailment", "neutral"]:
            related_id = item["match"].get("doc_id")
            per_key = ("duplicate", related_id)
            if counts_by_type["duplicate"] >= MAX_RESULTS_PER_TYPE:
                continue
            if related_id and per_related.get(per_key, 0) >= MAX_PER_RELATED_DOC:
                continue
            problems.append(Problem(
                type="duplicate",
                chunk_a=item["anchor"],
                chunk_b=item["match"],
                scores={"cosine": cos_score, "nli_confidence": conf}
            ))
            counts_by_type["duplicate"] += 1
            if related_id:
                per_related[per_key] = per_related.get(per_key, 0) + 1

    return problems
