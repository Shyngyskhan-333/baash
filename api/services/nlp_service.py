import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional

from src.retrieval.retriever import LegalRetriever
from src.reasoning.version_compare import semantic_diff_chunk


class NLPService:
    def __init__(self):
        self.retriever = LegalRetriever()

    def search(self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Hybrid BM25 + FAISS search with RRF fusion."""
        results = self.retriever.search_hybrid(query, top_k=50 if filters else top_k)
        if filters and "doc_id" in filters:
            results = [r for r in results if r.get("doc_id") == filters["doc_id"]]
        from src.embeddings.embedder import embed_text
        query_vec = embed_text(query, is_query=True).tolist()
        return {"results": results[:top_k], "query_vector": query_vec}

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Read parsed document JSON directly from disk."""
        import json
        from pathlib import Path
        try:
            p = Path(f"data/parsed/{doc_id}.json")
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None
        except Exception:
            return None

    def search_within_document(self, doc_id: str, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Search chunks within a single document."""
        return self.retriever.search_within_document(doc_id=doc_id, query=query, top_k=top_k)

    def analyze_document_fast(self, doc_id: str) -> Dict[str, Any]:
        """
        FAST document analysis using FAISS similarity only — NO NLI scan.
        Finds chunks of THIS document that have very similar chunks in OTHER documents.
        O(K * log N) instead of O(N²) — runs in milliseconds.
        """
        from src.embeddings.embedder import embed_texts
        import numpy as np, faiss as faiss_lib

        # Get all chunks belonging to this document
        doc_chunks = [m for m in self.retriever.metadata if m.get("doc_id") == doc_id]
        if not doc_chunks:
            return {"problems": []}

        # Embed document chunks
        doc_texts = [c["text"] for c in doc_chunks]
        vecs = embed_texts(doc_texts, is_query=False, batch_size=32).astype(np.float32)
        faiss_lib.normalize_L2(vecs)

        # Search for similar chunks in the index (top 5 per chunk)
        scores, indices = self.retriever.index.search(vecs, 6)

        THRESHOLD_DUPLICATE = 0.97
        THRESHOLD_SIMILAR = 0.90

        from dataclasses import dataclass
        from typing import Optional as Opt

        @dataclass
        class FastProblem:
            type: str
            chunk_a: dict
            chunk_b: dict
            scores: dict
            explanation: Opt[dict] = None

        problems = []
        seen = set()

        for i, (chunk, row_scores, row_indices) in enumerate(zip(doc_chunks, scores, indices)):
            for score, j in zip(row_scores, row_indices):
                if j < 0 or j >= len(self.retriever.metadata):
                    continue
                match = self.retriever.metadata[j]
                if match.get("doc_id") == doc_id:
                    continue  # Skip same-document matches

                pair_key = tuple(sorted([chunk.get("chunk_id", i), match.get("chunk_id", j)]))
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                score_f = float(score)
                if score_f >= THRESHOLD_DUPLICATE:
                    problems.append(FastProblem(
                        type="duplicate",
                        chunk_a=chunk,
                        chunk_b=match,
                        scores={"cosine": score_f},
                    ))
                elif score_f >= THRESHOLD_SIMILAR:
                    # Mark as potential contradiction (needs NLI to confirm, but we signal it)
                    problems.append(FastProblem(
                        type="contradiction",
                        chunk_a=chunk,
                        chunk_b=match,
                        scores={"cosine": score_f},
                    ))

        return {"problems": problems}

    # Keep old analyze_document as alias for analyze_document_fast
    def analyze_document(self, doc_id: str) -> Dict[str, Any]:
        return self.analyze_document_fast(doc_id)

    def compare_texts(self, text_a: str, text_b: str) -> Dict[str, Any]:
        return semantic_diff_chunk(text_a, text_b)


# Singleton — loads FAISS index once at startup
nlp_service = NLPService()
