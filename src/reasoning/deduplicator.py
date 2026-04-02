"""
Deduplicator Tool.
Инструмент для безвозвратного удаления дублирующихся логических кусков (chunk_b)
из исходных JSON файлов с сохранением их стройной иерархии (Статья -> Пункт).
"""
import json
from pathlib import Path
from tqdm import tqdm

from src.reasoning.detector import detect_all_problems
from src.retrieval.retriever import LegalRetriever

PARSED_DIR = Path("data/parsed")

def deduplicate_and_clean_database(retriever: LegalRetriever) -> int:
    """Находит дубликаты и вырезает их из исходных JSON файлов (data/parsed/*.json)."""
    print("Сканирование базы на предмет дублей (Cosine > 0.96 & Entailment)...")
    problems = detect_all_problems(retriever)
    duplicates = [p for p in problems if p.type == "duplicate"]
    
    if not duplicates:
        print("Дубликатов не найдено.")
        return 0
        
    print(f"Найдено {len(duplicates)} смысловых дублей. Начинаю зачистку JSON...")
    deleted_count = 0
    
    for dup in tqdm(duplicates, desc="Удаление из JSON"):
        chunk_b = dup.chunk_b  
        chunk_id = chunk_b['chunk_id']
        doc_id = chunk_id.split("_art")[0]
        
        json_path = PARSED_DIR / f"{doc_id}.json"
        
        if not json_path.exists():
            continue
            
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
                
        modified = False
        articles_to_keep = []
        
        for art in data.get("articles", []):
            original_len = len(art.get("chunks", []))
            art["chunks"] = [ch for ch in art.get("chunks", []) if ch.get("chunk_id") != chunk_id]
            
            if len(art["chunks"]) < original_len:
                modified = True
                deleted_count += (original_len - len(art["chunks"]))
                
            if len(art["chunks"]) > 0:
                articles_to_keep.append(art)
                
        if modified:
            data["articles"] = articles_to_keep
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
    print(f"Успешно удалено {deleted_count} дублирующихся кусков текста из файлов 'parsed'.")
    return deleted_count
