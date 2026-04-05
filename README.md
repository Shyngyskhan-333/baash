
<div align="center">
  <h1>LexLens</h1>
  <p><strong>AI-система снижения энтропии законодательства Республики Казахстан</strong></p>
  <p>Автоматическое обнаружение коллизий · Дублирований · Устаревших норм</p>

  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/FAISS-CPU-FF6F00?style=for-the-badge" alt="FAISS">
  
  <br><br>
  <strong>Для правительства и госорганов Казахстана</strong>
</div>

**Скриншоты:**

<img width="1280" height="680" alt="Image" src="https://github.com/user-attachments/assets/c56e7c66-783f-40a4-8627-6aba98e558f4" />
<img width="1280" height="680" alt="Image" src="https://github.com/user-attachments/assets/ccfe6685-38f9-4c11-8853-8c20f8316c90" />
<img width="1280" height="680" alt="Image" src="https://github.com/user-attachments/assets/a53937d3-c467-41b6-aec3-1e16cbac73eb" />
<img width="1280" height="680" alt="Image" src="https://github.com/user-attachments/assets/3c03883c-4142-41f3-98e3-238c47ddbc4d" />
<img width="507" height="913" alt="Image" src="https://github.com/user-attachments/assets/4140dfb8-ddd4-40e4-9e2c-1369219eccb5" />

---

## Демо

[Смотреть полное демо](https://www.youtube.com/watch?v=GVM50StfjBU)

---

## Что такое LexLens?

**LexLens** — это производственная система интеллектуального анализа НПА РК. Система автоматически парсит документы с портала [Әділет](https://adilet.zan.kz), строит векторную базу знаний и запускает многоуровневый пайплайн обнаружения проблем:

```text
Парсинг НПА → Чанкинг → Векторизация → Hybrid Search → NLI Детектор → LLM Объяснение
````

> **Провайдеры**: Поддерживается Azure OpenAI Compatible и полностью локальный Ollama

-----

## Функционал

| Модуль | Описание |
|--------|----------|
| **Гибридный поиск** | BM25 + семантический FAISS поиск с Reciprocal Rank Fusion |
| **Детектор коллизий** | NLI-модель (`rubert-tiny-bilingual`) для выявления противоречий O(N²) |
| **Анализ документа** | Быстрый FAISS-анализ О(K·log N) за \~100мс без блокировки |
| **AI Чат-помощник** | Вопросы по любому закону с контекстом из базы НПА |
| **Граф знаний** | PyVis-визуализация связей между НПА |
| **Heatmap коллизий** | Тепловая карта конфликтующих документов (Plotly) |
| **Семантический Diff** | Построчное сравнение редакций НПА с AI-резюме |
| **Локальный AI** | Qwen 2.5 / Llama через Ollama — 100% офлайн |
| **Облачный AI** | Azure OpenAI |
| **Настройки через UI** | Смена провайдера, API-ключей без перезапуска сервера |

-----

## Архитектура

```text
┌──────────────────────── Frontend (React 19 + Vite) ─────────────────────────┐
│  /          Поиск НПА     /analyze/:id   Анализ документа                   │
│  /diff      Сравнение     /audit         Глобальный аудит                   │
│  /graph     Граф & Map    /index         Индексация                         │
│  /settings  AI-настройки                                                    │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │ REST API
┌─────────────────────────────▼───────────────────────────────────────────────┐
│                         FastAPI Backend (:8000)                             │
│  Routers: search · analyze · chat · audit · diff · graph · index · settings │
└───────┬─────────────────────┬───────────────────────────┬───────────────────┘
        │                     │                           │
┌───────▼──────┐   ┌──────────▼────────┐   ┌─────────────▼──────────────────┐
│ FAISS HNSW   │   │  BM25 Okapi       │   │  AI Provider                   │
│ 384-dim      │   │  rank_bm25        │   │  Ollama │ Azure                │
│ CPU-only     │   │                   │   │  → data/ai_config.json         │
└───────┬──────┘   └──────────┬────────┘   └────────────────────────────────┘
        │                     │
┌───────▼─────────────────────▼──────────────────────────────────────────────┐
│                         src/ — ML Pipeline                                 │
│  embeddings/   · multilingual-e5-small (Sentence-Transformers)             │
│  retrieval/    · Hybrid BM25+FAISS + RRF                                   │
│  reasoning/    · NLI detector · LLM explainer · version compare            │
│  graph/        · PyVis knowledge graph                                     │
│  scraper/      · Adilet.zan.kz HTML parser                                 │
└────────────────────────────────────────────────────────────────────────────┘
```

**Модели ML (работают на CPU и GPU):**
| Модель | Задача | Размер |
|--------|--------|--------|
| `intfloat/multilingual-e5-small` | Векторизация чанков | \~120 MB |
| `cointegrated/rubert-tiny-bilingual-nli` | Детекция противоречий | \~45 MB |

-----

## Быстрый старт

### 1\. Клонирование и виртуальное окружение

```bash
cd https://github.com/Shyngyskhan-333/lexlens.git
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

На Linux/macOS: `source venv/bin/activate` и `cp .env.example .env`.

### 2\. Frontend

```bash
cd frontend
npm install
cd ..
```

### 3\. Запуск

**Терминал 1 — API:**

```bash
cd https://github.com/Shyngyskhan-333/lexlens.git
.\venv\Scripts\activate
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

**Терминал 2 — UI:**

```bash
cd frontend
npm run dev
```

Откройте `http://localhost:5173`. Swagger API: `http://127.0.0.1:8000/docs`.

-----

## Режим быстрого теста

Для проверки UI без долгой пересборки графа: подставляются кэшированные граф/heatmap, ускоренные флаги интерфейса.

**Backend:**

```powershell
$env:ENV_FILE=".env.quicktest"
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**

```bash
cd frontend
npm run dev:quicktest
```

Алиас: `npm run dev:demo` → то же самое. В `.env.quicktest` заданы `QUICK_TEST_MODE=1` и `GRAPH_FAST_MODE=1`. Подробности — [docs/TECHNICAL.md](https://www.google.com/search?q=docs/TECHNICAL.md) §8.

-----

## Документация

| Документ | Содержание |
|----------|------------|
| [docs/TECHNICAL.md](https://www.google.com/search?q=docs/TECHNICAL.md) | Полная техдокументация: таблица REST API, каталог data/, ML-стек, env, расширение, тесты, деплой |
| [README\_QUICK\_START.md](https://www.google.com/search?q=README_QUICK_START.md) | Краткая шпаргалка команд |
| Swagger | `http://127.0.0.1:8000/docs` при запущенном API |

-----

## Расширение LexLens

  - Папка: `extension/`
  - Chrome → `chrome://extensions` → режим разработчика → «Загрузить распакованное»
  - Для поиска связанных НПА должен быть доступен API на `http://127.0.0.1:8000`
  - Настройка моделей для чата — внутри сайдбара расширения (storage + опционально облачные провайдеры)

Детали сообщений service worker и прав — [docs/TECHNICAL.md](https://www.google.com/search?q=docs/TECHNICAL.md) §9.

-----

## Данные и модели

  - Источник текстов: adilet.zan.kz (и при необходимости архивные URL).
  - Локальные артефакты: `data/parsed/`, `data/faiss/`, `data/embeddings/`, `data/cache/`.
  - CLI для индексации и отладки: `python pipeline.py --help`

-----

## Тесты

```bash
.\venv\Scripts\activate
python -m unittest tests.test_api_smoke -v
```

-----

## Безопасность для госсектора

LexEntropy поддерживает **полностью изолированный** режим работы:

1.  **Локальный AI** — Ollama + Qwen 2.5:7b, данные не выходят за пределы сервера
2.  **Офлайн-модели** — e5-small и rubert-tiny скачиваются один раз в `data/models/`
3.  **Нет внешних запросов** — при `AI_PROVIDER=ollama` все вызовы идут на `localhost:11434`
4.  **API ключи не в коде** — хранятся в `.env` (не коммитится) и `data/ai_config.json`

-----

## Стек технологий

| Уровень | Технологии |
|---------|-----------|
| **Frontend** | React 19, Vite 6, TailwindCSS 3, Zustand, Axios, Lucide, React-Plotly, PyVis (iframe) |
| **Backend** | FastAPI, Uvicorn, Pydantic v2 |
| **Search** | FAISS (IndexHNSWFlat, CPU), rank-bm25, Sentence-Transformers |
| **NLP** | HuggingFace Transformers, intfloat/multilingual-e5-small, cointegrated/rubert-tiny-bilingual-nli |
| **AI** | OpenAI SDK, Anthropic SDK, httpx (Ollama) |
| **Visualization** | PyVis (граф), Plotly (heatmap) |
| **Data** | JSON (parsed), Pickle (FAISS/BM25 индексы) |

-----

## Связь

Проект разработан для анализа законодательства **Республики Казахстан**.  
База НПА: [Әділет — Информационно-правовая система](https://adilet.zan.kz)

-----

Built by baash for Kazakhstan Legal Tech

Decentrathon 5.0 

2026
