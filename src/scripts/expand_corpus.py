import argparse
import json
import re
from collections import deque
from datetime import datetime
from pathlib import Path

from src.retrieval.retriever import LegalRetriever
from src.scraper.adilet_scraper import parse_batch

DOC_ID_RE = re.compile(r"^[A-Z]\d{8,9}_?$")
ARCHIVE_RE = re.compile(r"_\d{8}$")

THEME_KEYWORDS = [
    "труд",
    "работ",
    "соц",
    "госслуж",
    "служб",
    "государств",
    "администра",
    "процедур",
    "налог",
    "бюджет",
    "здравоохран",
    "образован",
    "миграц",
    "пенси",
    "страхован",
    "эколог",
    "энерг",
    "земл",
    "водн",
    "закуп",
    "правоохран",
    "суд",
    "процесс",
    "лиценз",
    "регламент",
    "правил",
    "порядок",
    "контроль",
    "надзор",
    "реестр",
    "комитет",
    "министерств",
    "агентств",
    "вопросы",
    "утвержден",
]

def is_valid_id(doc_id: str) -> bool:
    if not doc_id or not DOC_ID_RE.match(doc_id):
        return False
    if ARCHIVE_RE.search(doc_id):
        return False
    return True

def is_theme_title(title: str) -> bool:
    if not title:
        return False
    t = title.lower()
    return any(k in t for k in THEME_KEYWORDS)

def load_existing(parsed_dir: Path) -> tuple[set, set]:
    existing_ids = set()
    refs = set()
    for file_path in parsed_dir.glob("*.json"):
        doc_id = file_path.stem
        existing_ids.add(doc_id)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            for ref in doc.get("references", []):
                if is_valid_id(ref):
                    refs.add(ref)
        except Exception:
            continue
    return existing_ids, refs

def expand_corpus(
    target_total: int,
    theme_ratio: float,
    batch_size: int,
    output_path: Path,
    dry_run: bool = False,
) -> dict:
    parsed_dir = Path("data/parsed")
    existing_ids, initial_refs = load_existing(parsed_dir)

    theme_target = int(round(target_total * theme_ratio))
    graph_target = target_total - theme_target

    queue = deque(sorted(initial_refs))
    seen = set(existing_ids)
    selected_ids = set()
    selected_theme = set()
    selected_graph = set()

    retriever = LegalRetriever()
    to_index = []

    while queue and len(selected_ids) < target_total:
        batch = []
        while queue and len(batch) < batch_size:
            did = queue.popleft()
            if did in seen:
                continue
            seen.add(did)
            if not is_valid_id(did):
                continue
            if did in existing_ids or did in selected_ids:
                continue
            batch.append(did)

        if not batch:
            continue

        docs = parse_batch(batch) if not dry_run else []
        for doc in docs:
            doc_id = doc.get("doc_id")
            if not doc_id or doc_id in existing_ids or doc_id in selected_ids:
                continue

            title = doc.get("title", "")
            themed = is_theme_title(title)

            if themed and len(selected_theme) < theme_target:
                selected_theme.add(doc_id)
                selected_ids.add(doc_id)
                to_index.append(doc)
            elif len(selected_graph) < graph_target:
                selected_graph.add(doc_id)
                selected_ids.add(doc_id)
                to_index.append(doc)
            elif themed and len(selected_theme) < theme_target:
                selected_theme.add(doc_id)
                selected_ids.add(doc_id)
                to_index.append(doc)
            elif len(selected_ids) < target_total:
                selected_graph.add(doc_id)
                selected_ids.add(doc_id)
                to_index.append(doc)

            for ref in doc.get("references", []):
                if ref not in seen and is_valid_id(ref):
                    queue.append(ref)

            if len(selected_ids) >= target_total:
                break

        if to_index and not dry_run:
            retriever.add_documents(to_index)
            to_index = []

    if to_index and not dry_run:
        retriever.add_documents(to_index)

    report = {
        "created_at": datetime.now().isoformat(),
        "target_total": target_total,
        "theme_target": theme_target,
        "graph_target": graph_target,
        "theme_name": "soc-trud + gos-upravlenie",
        "theme_keywords": THEME_KEYWORDS,
        "selected_total": len(selected_ids),
        "selected_theme": sorted(selected_theme),
        "selected_graph": sorted(selected_graph),
        "missing_total": max(0, target_total - len(selected_ids)),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--theme-ratio", type=float, default=0.30)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--output", type=str, default="data/added_ids_500.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = expand_corpus(
        target_total=args.count,
        theme_ratio=args.theme_ratio,
        batch_size=args.batch_size,
        output_path=Path(args.output),
        dry_run=args.dry_run,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()