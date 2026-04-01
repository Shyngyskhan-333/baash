"""
Интеллектуальный детектор коллизий (Reasoning Pipeline).
Реализует CPU-оптимизированный алгоритм:
1. Retrieval (Hybrid Bulk Search) -> top-10
2. Filter (Cosine > 0.88) -> Smart Filter
3. Parallel Batch NLI (ruBERT-tiny-bilingual)
4. LLM Explain (Только для Топ-K подтвержденных противоречий).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import faiss
import os
from tqdm import tqdm

from src.reasoning.explainer import explain_contradiction
from src.reasoning.nli import check_contradictions_batch
from src.retrieval.retriever import LegalRetriever
from src.embeddings.embedder import embed_texts


@dataclass
class Problem:
    type: str  # "contradiction" | "duplicate" | "outdated"
    chunk_a: dict
    chunk_b: dict
    scores: dict
    explanation: Optional[dict] = None



def detect_all_problems(retriever: LegalRetriever, top_k_explain: int = 10) -> List[Problem]:
    """
    Проходит по всей базе чанков и ищет коллизии, дубликаты и устаревшие нормы.
    Оптимизировано для CPU: Batch Vector Search + Parallel NLI + Caching.
    """
    if not retriever.metadata:
        return []
        
    problems = []
    
    outdated_anchor = (
        "Данная норма официально отменена и утратила юридическую силу. "
        "Нормативный акт признан недействующим и не подлежит применению. "
        "Положение утратило силу в связи с принятием нового законодательства. "
        "Текст исключён из действующей редакции кодекса как утративший силу."
    )
    
    outdated_candidates = retriever.search_hybrid(outdated_anchor, top_k=100)
    for match in outdated_candidates:
        if match.get("cosine_score", 0.0) > 0.88:
            problems.append(Problem(
                type="outdated",
                chunk_a=match,
                chunk_b=match,
                scores={"cosine": match.get("cosine_score"), "nli_confidence": 1.0},
                explanation={"verdict": "Норма семантически классифицирована как 'Утратившая силу'."}
            ))
            
    all_texts = [m["text"] for m in retriever.metadata]
    
    print(f"[Instant Mode] Извлечение {len(retriever.metadata)} готовых векторов из базы...")
    try:
        vecs_fp32 = retriever.index.reconstruct_n(0, len(retriever.metadata))
    except Exception as e:
        print(f"FAISS reconstruct_n не поддерживается: {e}. Используем медленную векторизацию...")
        vecs_fp16 = embed_texts(all_texts, is_query=True, batch_size=64)
        vecs_fp32 = vecs_fp16.astype(np.float32)
        faiss.normalize_L2(vecs_fp32)
    
    print("[Batch Mode] FAISS Bulk Search: Сравнение миллионов пар...")
    faiss_scores, faiss_indices = retriever.index.search(vecs_fp32, 10)
    
    print("[NumPy Mode] Фильтрация релевантных пар (Threshold > 0.90)...")
    
    threshold = 0.90
    mask = faiss_scores > threshold
    rows, cols = np.where(mask)
    
    pairs_to_check = []
    pair_metadata = []
    seen_pairs = set()
    
    for r, c in zip(rows, cols):
        i = int(r)
        j = int(faiss_indices[r, c])
        
        if j < 0 or j == i:
            continue
            
        anchor_chunk = retriever.metadata[i]
        match = retriever.metadata[j]
        
        if match["doc_id"] == anchor_chunk["doc_id"]:
            continue
            
        score = float(faiss_scores[r, c])
        
        p_id = tuple(sorted([anchor_chunk["chunk_id"], match["chunk_id"]]))
        if p_id in seen_pairs:
            continue
        seen_pairs.add(p_id)
        
        pairs_to_check.append((anchor_chunk["text"], match["text"], anchor_chunk["chunk_id"], match["chunk_id"]))
        pair_metadata.append((anchor_chunk, match, score))

    if not pairs_to_check:
        return problems

    print(f"[Sequential NLI] Запуск NLI на {len(pairs_to_check)} пар...")
    
    # На Windows multiprocessing.Pool + torch/transformers вызывает зависон.
    # Используем последовательные батчи — безопасно и достаточно быстро для < 10k пар.
    nli_results = check_contradictions_batch(pairs_to_check, batch_size=32)
    
    print(f"Анализ результатов и запуск LLM Explain (Top-{top_k_explain})...")
    
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
    for item in scored_pairs:
        label = item["nli_label"]
        conf = item["nli_conf"]
        cos_score = item["cos_score"]
        
        explanation = None
        if label == "contradiction" and conf > 0.6:
            if explained_count < top_k_explain:
                explanation = explain_contradiction(
                    text_a=item["anchor"]["text"], 
                    text_b=item["match"]["text"], 
                    law_a=item["anchor"]["doc_title"], 
                    law_b=item["match"]["doc_title"]
                )
                explained_count += 1
            
            problems.append(Problem(
                type="contradiction",
                chunk_a=item["anchor"],
                chunk_b=item["match"],
                scores={"cosine": cos_score, "nli_confidence": conf},
                explanation=explanation
            ))
            
        elif cos_score > 0.96 and label in ["entailment", "neutral"]:
            problems.append(Problem(
                type="duplicate",
                chunk_a=item["anchor"],
                chunk_b=item["match"],
                scores={"cosine": cos_score, "nli_confidence": conf}
            ))
            
    return problems
