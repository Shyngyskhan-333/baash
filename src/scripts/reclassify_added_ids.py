import argparse
import json
from pathlib import Path

from src.scripts.expand_corpus import THEME_KEYWORDS, is_theme_title

def load_titles(doc_ids: list[str]) -> dict[str, str]:
    titles = {}
    parsed_dir = Path("data/parsed")
    for doc_id in doc_ids:
        path = parsed_dir / f"{doc_id}.json"
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            titles[doc_id] = doc.get("title", "")
        except Exception:
            continue
    return titles

def reclassify(input_path: Path, output_path: Path) -> dict:
    with open(input_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    all_ids = sorted(set(payload.get("selected_theme", []) + payload.get("selected_graph", [])))
    if not all_ids:
        return payload

    theme_target = payload.get("theme_target", int(round(len(all_ids) * 0.3)))
    titles = load_titles(all_ids)

    theme_candidates = [doc_id for doc_id in all_ids if is_theme_title(titles.get(doc_id, ""))]
    if len(theme_candidates) >= theme_target:
        selected_theme = theme_candidates[:theme_target]
    else:
        remaining = [doc_id for doc_id in all_ids if doc_id not in set(theme_candidates)]
        selected_theme = theme_candidates + remaining[: max(0, theme_target - len(theme_candidates))]

    selected_theme_set = set(selected_theme)
    selected_graph = [doc_id for doc_id in all_ids if doc_id not in selected_theme_set]

    payload["theme_name"] = "regulatory-licensing + social-labor"
    payload["theme_keywords"] = THEME_KEYWORDS
    payload["selected_theme"] = selected_theme
    payload["selected_graph"] = selected_graph
    payload["selected_total"] = len(all_ids)
    payload["missing_total"] = max(0, payload.get("target_total", len(all_ids)) - len(all_ids))

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="data/added_ids_500.json")
    parser.add_argument("--output", type=str, default="data/added_ids_500.json")
    args = parser.parse_args()

    result = reclassify(Path(args.input), Path(args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()