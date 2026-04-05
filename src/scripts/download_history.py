import asyncio
import glob
from pathlib import Path
from src.scraper.adilet_scraper import fetch_versions

async def main():
    parsed_dir = Path("data/parsed")
    if not parsed_dir.exists():
        print("Папка data/parsed не найдена.")
        return

    all_files = glob.glob(str(parsed_dir / "*.json"))

    unique_docs = set()
    for fp in all_files:
        filename = Path(fp).stem

        if "_" not in filename:
            unique_docs.add(filename)

    print(f"Найдено базовых законов: {len(unique_docs)}")
    print("Начинаю загрузку прошлых версий (по 2 на каждый)...")

    for doc_id in unique_docs:
        await fetch_versions(doc_id)

    print("Завершено! Все исторические версии сохранены.")

if __name__ == "__main__":
    asyncio.run(main())