import asyncio
from src.retrieval.retriever import LegalRetriever
from src.reasoning.detector import detect_all_problems
from src.graph.knowledge_graph import LegalKnowledgeGraph

async def main():
    print("Инициализация Retriever...")
    retriever = LegalRetriever()

    if retriever.index.ntotal == 0:
        print("Индекс пуст. Сначала добавьте документы!")
        return

    print(f"В базе {retriever.index.ntotal} чанков. Начинаю глобальный аудит коллизий...")

    problems = await detect_all_problems(
        retriever=retriever,
        top_k_explain=0,
        doc_ids=None,
        ai_caller=None
    )

    print(f"Найдено {len(problems)} потенциальных связей (коллизии, дубликаты, отмененные).")

    graph = LegalKnowledgeGraph()
    graph.build_from_detector_problems(problems)

    print("Готово! Все связи записаны в кэш. Граф теперь будет открываться мгновенно.")

if __name__ == "__main__":
    asyncio.run(main())