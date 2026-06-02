import asyncio
import concurrent.futures
import re
from typing import List, Dict, Any, Optional

from src.retrieval.retriever import LegalRetriever
from src.reasoning.version_compare import semantic_diff_chunk
from src.search.service import SearchService

class NLPService:
    def __init__(self):
        self.retriever = LegalRetriever()
        self.search_service = SearchService(self.retriever)

    def search(self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None, doc_ids: Optional[List[str]] = None) -> Dict[str, Any]:

        search_data = self.search_service.search(query, top_k=top_k, filters=filters, doc_ids=doc_ids)
        from src.embeddings.embedder import embed_text
        try:
            query_vec = embed_text(query, is_query=True).tolist()
        except Exception:
            query_vec = []
        return {"results": search_data["results"], "query_vector": query_vec}

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:

        import json
        from pathlib import Path
        if not doc_id or doc_id.strip() != doc_id:
            return None
        if any(x in doc_id for x in ("..", "/", "\\")):
            return None
        try:
            p = Path("data/parsed") / f"{doc_id}.json"
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None
        except Exception:
            return None

    def search_within_document(self, doc_id: str, query: str, top_k: int) -> List[Dict[str, Any]]:

        return self.retriever.search_within_document(doc_id=doc_id, query=query, top_k=top_k)

    def analyze_document_fast(self, doc_id: str, doc_ids: Optional[List[str]] = None) -> Dict[str, Any]:

        from src.embeddings.embedder import embed_texts
        import numpy as np, faiss as faiss_lib
        from src.graph.knowledge_graph import LegalKnowledgeGraph

        doc_info = self.get_document_by_id(doc_id)
        if doc_info:
            graph = LegalKnowledgeGraph()
            graph.ensure_doc_node(doc_id, doc_info.get("title", doc_id))

        doc_chunks = [m for m in self.retriever.metadata if m.get("doc_id") == doc_id]
        if not doc_chunks:
            return {"problems": []}

        doc_texts = [c["text"] for c in doc_chunks]
        try:
            vecs = embed_texts(doc_texts, is_query=False, batch_size=32).astype(np.float32)
        except Exception as error:
            print(f"[ANALYZE_FALLBACK] Embeddings unavailable: {error}")
            return {"problems": []}
        faiss_lib.normalize_L2(vecs)

        search_depth = 50 if doc_ids else 6
        scores, indices = self.retriever.index.search(vecs, search_depth)

        THRESHOLD_DUPLICATE = 0.985
        THRESHOLD_SIMILAR = 0.96
        MIN_NLI_CONFIDENCE = 0.85
        MIN_TOKEN_OVERLAP = 0.12
        MAX_CANDIDATES_PER_CHUNK = 4 if doc_ids else 2

        from dataclasses import dataclass
        from typing import Optional as Opt

        @dataclass
        class FastProblem:
            type: str
            chunk_a: dict
            chunk_b: dict
            scores: dict
            explanation: Opt[dict] = None

        candidate_pairs = []
        pair_context = []
        seen = set()
        token_cache = {}

        def token_set(text: str) -> set:
            import re
            return set(re.findall(r"(?u)\b[\w-]{3,}\b", text.lower()))

        def get_tokens(chunk_id: str, text: str) -> set:
            cached = token_cache.get(chunk_id)
            if cached is not None:
                return cached
            tokens = token_set(text)
            token_cache[chunk_id] = tokens
            return tokens

        for i, (chunk, row_scores, row_indices) in enumerate(zip(doc_chunks, scores, indices)):
            per_chunk_candidates = []
            for score, j in zip(row_scores, row_indices):
                if j < 0 or j >= len(self.retriever.metadata):
                    continue
                match = self.retriever.metadata[j]
                match_doc_id = match.get("doc_id")

                if match_doc_id == doc_id:
                    continue

                if doc_ids and match_doc_id not in doc_ids:
                    continue

                pair_key = tuple(sorted([chunk.get("chunk_id", i), match.get("chunk_id", j)]))
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                score_f = float(score)
                if score_f < THRESHOLD_SIMILAR:
                    continue
                text_a = chunk["text"]
                text_b = match["text"]

                if len(text_a) < 120 or len(text_b) < 120:
                    continue
                tokens_a = get_tokens(chunk.get("chunk_id", str(i)), text_a)
                tokens_b = get_tokens(match.get("chunk_id", str(j)), text_b)
                if tokens_a and tokens_b:
                    overlap = len(tokens_a & tokens_b) / max(1, len(tokens_a | tokens_b))
                    if overlap < MIN_TOKEN_OVERLAP:
                        continue
                match_id = match.get("chunk_id", str(j))
                per_chunk_candidates.append((score_f, text_a, text_b, chunk, match, match_id))

            if per_chunk_candidates:
                per_chunk_candidates.sort(key=lambda x: x[0], reverse=True)
                for score_f, text_a, text_b, chunk, match, match_id in per_chunk_candidates[:MAX_CANDIDATES_PER_CHUNK]:
                    candidate_pairs.append((text_a, text_b, chunk.get("chunk_id", str(i)), match_id))
                    pair_context.append((chunk, match, score_f))

        problems = []
        if candidate_pairs:
            from src.reasoning.nli import check_contradictions_batch

            nli_results = check_contradictions_batch(candidate_pairs, batch_size=16)
            for (chunk, match, score_f), nli in zip(pair_context, nli_results):
                label = nli.get("label")
                confidence = float(nli.get("confidence", 0.0))
                scores = {"cosine": score_f, "nli_confidence": confidence}

                if label == "contradiction" and confidence >= MIN_NLI_CONFIDENCE and score_f >= 0.965:
                    problems.append(FastProblem(
                        type="contradiction",
                        chunk_a=chunk,
                        chunk_b=match,
                        scores=scores,
                    ))
                elif score_f >= THRESHOLD_DUPLICATE and label != "contradiction":
                    problems.append(FastProblem(
                        type="duplicate",
                        chunk_a=chunk,
                        chunk_b=match,
                        scores=scores,
                    ))

        if problems:

            capped = {}
            for p in problems:
                key = (p.chunk_a.get("doc_id"), p.chunk_a.get("article_number"), p.type)
                capped.setdefault(key, [])
                capped[key].append(p)
            trimmed = []
            for key, items in capped.items():
                items.sort(key=lambda x: x.scores.get("nli_confidence", 0.0), reverse=True)
                trimmed.extend(items[:5])
            problems = trimmed

            related_cap = {}
            final = []
            for p in sorted(problems, key=lambda x: x.scores.get("nli_confidence", 0.0), reverse=True):
                related_id = p.chunk_b.get("doc_id")
                related_cap.setdefault((related_id, p.type), 0)
                if related_cap[(related_id, p.type)] >= 3:
                    continue
                related_cap[(related_id, p.type)] += 1
                final.append(p)
            problems = final[:120]
            try:
                from src.graph.knowledge_graph import LegalKnowledgeGraph
                graph = LegalKnowledgeGraph()
                graph.append_problems(problems, clear=False)
            except Exception as e:
                print(f"[GRAPH_UPDATE_ERROR] {e}")

        return {"problems": problems}

    def analyze_document(self, doc_id: str, doc_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        return self.analyze_document_fast(doc_id, doc_ids=doc_ids)

    def compare_texts(self, text_a: str, text_b: str) -> Dict[str, Any]:
        return semantic_diff_chunk(text_a, text_b)

nlp_service = NLPService()
