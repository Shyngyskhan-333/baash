"""
Корневой CLI скрипт для запуска Legal RAG System (CPU-Оптимизированной).
"""
import argparse
import sys
from pprint import pprint

from src.reasoning.detector import detect_all_problems
from src.retrieval.retriever import LegalRetriever
from src.scraper.adilet_scraper import parse_batch


def build_index(doc_ids: list):
    print("1. Скачивание и иерархический парсинг НПА (Adilet)...")
    docs = parse_batch(doc_ids)
    
    if not docs:
        print("Нет новых документов для добавления.")
        return
        
    print("\n2. Индексирование в гибридную базу (e5-small + FAISS HNSW + BM25)...")
    retriever = LegalRetriever()
    added = retriever.add_documents(docs)
    print(f"\nУспешно добавлено {added} новых логических чанков в базу.")


def query_search(q: str):
    print(f"Гибридный поиск (BM25 + FAISS RRF): '{q}'\n")
    retriever = LegalRetriever()
    results = retriever.search_hybrid(q, top_k=5)
    
    if not results:
        print("База данных пуста или ничего не найдено.")
        return
        
    for i, r in enumerate(results, 1):
        print(f"{i}. [RRF: {r['rrf_score']:.4f} | Cosine: {r['cosine_score']:.4f} | BM25: {r['bm25_score']:.4f}]")
        print(f"Документ: {r['doc_title']}, Статья: {r['article_number']}")
        print(f"Текст:\n{r['text'][:300]}...\n")


def detect_collisions():
    print("Запуск полного пайплайна интеллектуального детектора...")
    print("Схема: Одиночный поиск (BM25+FAISS) -> Фильтр Cosine > 0.9 -> Top-5 -> DeBERTa-mnli -> LLM")
    
    retriever = LegalRetriever()
    problems = detect_all_problems(retriever)
    
    print(f"\nАнализ завершен. Найдено {len(problems)} проблем (коллизий и дубликатов).")
    for i, p in enumerate(problems, 1):
        print("-" * 80)
        print(f"Проблема #{i}: {p.type.upper()}")
        print(f"Норма А: {p.chunk_a['doc_title']} ({p.chunk_a['article_number']})")
        print(f"Норма Б: {p.chunk_b['doc_title']} ({p.chunk_b['article_number']})")
        print(f"Метрики: {p.scores}")
        
        if p.explanation:
            print("\nОбъяснение алгоритма (JSON-структура):")
            pprint(p.explanation)


def clean_database():
    from src.reasoning.deduplicator import deduplicate_and_clean_database
    
    print("Инициализация зачистки JSON-файлов от дубликатов...")
    retriever = LegalRetriever()
    deleted = deduplicate_and_clean_database(retriever)
    
    if deleted > 0:
        print("\nУдаление завершено. Вызываю пересборку FAISS индекса для синхронизации...")
        retriever.rebuild_index()
    else:
        print("База уже очищена или пуста.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("--help")
        
    parser = argparse.ArgumentParser(description="Legal Entropy RAG System (CPU-Оптимизация)")
    parser.add_argument(
        "--build-index", 
        nargs="+", 
        help="Список ID документов (مثلا: K1500000377 K1400000266) для скачивания и индексации"
    )
    parser.add_argument(
        "--query", 
        type=str, 
        help="Текстовый запрос для поиска по гибридной RRM-базе"
    )
    parser.add_argument(
        "--detect-all", 
        action="store_true", 
        help="Запустить пайплайн поиска всех коллизий/противоречий"
    )
    parser.add_argument(
        "--clean-duplicates",
        action="store_true",
        help="Автоматически уничтожить смысловые дубли из parsed/*.json и пересобрать индекс FAISS"
    )
    
    args = parser.parse_args()
    
    if args.build_index:
        build_index(args.build_index)
    elif args.query:
        query_search(args.query)
    elif args.detect_all:
        detect_collisions()
    elif args.clean_duplicates:
        clean_database()
