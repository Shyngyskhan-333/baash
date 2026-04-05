
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from src.scraper.adilet_scraper import parse_batch
from src.retrieval.retriever import LegalRetriever

DATA_DIR = Path("data")
PARSED_DIR = DATA_DIR / "parsed"

def _load_existing_ids() -> set[str]:
    return {p.stem for p in PARSED_DIR.glob("*.json")}

def _iter_parsed_docs() -> Iterable[dict]:
    for p in PARSED_DIR.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                yield json.load(f)
        except Exception:
            continue

def _build_reference_stats() -> tuple[Counter, dict[str, set[str]]]:

    ref_counts: Counter = Counter()
    ref_sources: dict[str, set[str]] = defaultdict(set)

    for doc in _iter_parsed_docs():
        src_id = doc.get("doc_id")
        for ref in doc.get("references", []):
            ref_counts[ref] += 1
            if src_id:
                ref_sources[ref].add(src_id)
    return ref_counts, ref_sources

def _select_ids(
    target_total: int,
    ratio_linked: float,
    min_theme_sources: int,
) -> list[str]:
    existing = _load_existing_ids()
    ref_counts, ref_sources = _build_reference_stats()

    candidates = [r for r in ref_counts.keys() if r not in existing]
    if not candidates:
        return []

    def score_key(ref_id: str) -> tuple[int, int, str]:
        return (len(ref_sources.get(ref_id, set())), ref_counts[ref_id], ref_id)

    candidates_sorted = sorted(candidates, key=score_key, reverse=True)

    linked_target = int(round(target_total * ratio_linked))
    thematic_target = target_total - linked_target

    linked = []
    remaining = []
    for ref_id in candidates_sorted:
        if len(linked) < linked_target:
            linked.append(ref_id)
        else:
            remaining.append(ref_id)

    thematic = []
    for ref_id in remaining:
        if len(ref_sources.get(ref_id, set())) >= min_theme_sources:
            thematic.append(ref_id)
        if len(thematic) >= thematic_target:
            break

    if len(thematic) < thematic_target:

        for ref_id in remaining:
            if ref_id in thematic:
                continue
            thematic.append(ref_id)
            if len(thematic) >= thematic_target:
                break

    selected = linked + thematic
    return selected[:target_total]

def _save_selection(doc_ids: list[str]) -> Path:
    out_dir = DATA_DIR / "selections"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"adilet_expand_{ts}.txt"
    out_path.write_text("\n".join(doc_ids), encoding="utf-8")
    return out_path

def main() -> None:
    parser = argparse.ArgumentParser(description="Expand Adilet corpus from existing references.")
    parser.add_argument("--target", type=int, default=500, help="Number of new doc IDs to add.")
    parser.add_argument("--ratio-linked", type=float, default=0.7, help="Share of IDs from linked refs.")
    parser.add_argument("--min-theme-sources", type=int, default=2, help="Min distinct source docs for 'thematic' refs.")
    args = parser.parse_args()

    selected = _select_ids(args.target, args.ratio_linked, args.min_theme_sources)
    if not selected:
        print("No new references found to add.")
        return

    out_path = _save_selection(selected)
    print(f"Selected {len(selected)} doc IDs. Saved list to: {out_path}")

    print("Downloading & parsing selected documents...")
    docs = parse_batch(selected)
    if not docs:
        print("No new documents were parsed.")
        return

    print("Indexing into FAISS/BM25...")
    retriever = LegalRetriever()
    added = retriever.add_documents(docs)
    print(f"Indexed {added} new chunks.")

if __name__ == "__main__":
    main()