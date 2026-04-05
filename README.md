# LexLens — AI-система анализа законодательства РК

**Кейс:** 1. Законодательная энтропия (Decentrathon 5.0 / AI for Government)

**LexLens** помогает юристам и аналитикам выявлять **противоречия, дублирования и устаревшие нормы**, строить **граф связей** между НПА и получать **объяснимые** ответы (ретривер + LLM). В репозитории: веб-приложение (React + Vite), API (FastAPI), ML-пайплайн на CPU и браузерное расширение Chrome с тем же именем.

---

## Содержание

- [Возможности](#возможности)
- [Архитектура](#архитектура)
- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [Режим быстрого теста](#режим-быстрого-теста)
- [Документация](#документация)
- [Расширение LexLens](#расширение-lexlens)
- [Данные и модели](#данные-и-модели)
- [Тесты](#тесты)
- [Ограничения и ответственность](#ограничения-и-ответственность)
- [Лицензия](#лицензия)

---

## Возможности

| Область | Описание |
|---------|----------|
| **Поиск** | Гибридный **BM25 + FAISS + RRF** по чанкам НПА |
| **Анализ** | `GET /api/v1/analyze/{doc_id}` — смысловой разбор текста документа (LLM), риски и связанные акты |
| **Аудит** | `POST /api/v1/audit/detect` — NLI и эвристики по коллизиям в масштабе корпуса или выбранного scope |
| **Граф** | `GET /api/v1/graph/html` и `/graph/heatmap` — визуализация и тепловая карта |
| **Diff** | Семантическое сравнение редакций |
| **Чат** | `POST /api/v1/chat` с RAG; поле `explanation` отражает логику ретривера |
| **Настройки AI** | UI `/settings` и файл `data/ai_config.json`; провайдеры: Ollama, OpenAI, Azure, Anthropic, Mock |

Подробные контракты API, структура `data/`, модели и эксплуатация — в **[docs/TECHNICAL.md](docs/TECHNICAL.md)**.

---

## Архитектура

```
Frontend (React + Vite + TypeScript)     extension/ (Chrome MV3, LexLens)
         │                                          │
         └────────────────┬─────────────────────────┘
                          │ HTTP /api/v1
                   FastAPI (api/)
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   nlp_service      ai_provider     роутеры search,
   (ретривер)       (LLM)           analyze, audit, graph, …
         │
         ▼
   src/retrieval, src/embeddings, src/reasoning, src/graph, src/scraper
```

- **Индексация**: скрапинг Adilet → JSON в `data/parsed/` → чанки → эмбеддинги **multilingual-e5-small** → FAISS + BM25.
- **Аудит**: кандидаты из ретривера → **rubert-tiny-bilingual-nli** → при необходимости пояснения через LLM.

---

## Требования

- **Python** 3.10+
- **Node.js** 18+
- **RAM** ориентировочно 4–8 GB (загрузка PyTorch и трансформеров)
- Диск под кэш моделей в `data/models/`

Все команды API и пути к `data/` предполагают **текущий каталог = корень репозитория** (папка с `api/`, `src/`, `data/`).

---

## Быстрый старт

### 1. Клонирование и виртуальное окружение

```powershell
cd <путь-к-репозиторию>
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

На Linux/macOS: `source venv/bin/activate` и `cp .env.example .env`.

### 2. Frontend

```powershell
cd frontend
npm install
cd ..
```

### 3. Запуск

**Терминал 1 — API:**

```powershell
cd <путь-к-репозиторию>
.\venv\Scripts\activate
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

**Терминал 2 — UI:**

```powershell
cd frontend
npm run dev
```

Откройте **http://localhost:5173**. Swagger API: **http://127.0.0.1:8000/docs**.

---

## Режим быстрого теста

Для проверки UI без долгой пересборки графа: подставляются кэшированные граф/heatmap, ускоренные флаги интерфейса.

**Backend:**

```powershell
$env:ENV_FILE=".env.quicktest"
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**

```powershell
cd frontend
npm run dev:quicktest
```

Алиас: `npm run dev:demo` → то же самое. В `.env.quicktest` заданы `QUICK_TEST_MODE=1` и `GRAPH_FAST_MODE=1`. Подробности — [docs/TECHNICAL.md](docs/TECHNICAL.md) §8.

---

## Документация

| Документ | Содержание |
|----------|------------|
| **[docs/TECHNICAL.md](docs/TECHNICAL.md)** | Полная техдокументация: таблица REST API, каталог `data/`, ML-стек, env, расширение, тесты, деплой |
| **[README_QUICK_START.md](README_QUICK_START.md)** | Краткая шпаргалка команд |
| **Swagger** | `http://127.0.0.1:8000/docs` при запущенном API |

---

## Расширение LexLens

- Папка: **`extension/`**
- Chrome → `chrome://extensions` → режим разработчика → «Загрузить распакованное»
- Для поиска связанных НПА должен быть доступен API на **http://127.0.0.1:8000**
- Настройка моделей для чата — внутри сайдбара расширения (storage + опционально облачные провайдеры)

Детали сообщений service worker и прав — [docs/TECHNICAL.md](docs/TECHNICAL.md) §9.

---

## Данные и модели

- Источник текстов: **adilet.zan.kz** (и при необходимости архивные URL).
- Локальные артефакты: `data/parsed/`, `data/faiss/`, `data/embeddings/`, `data/cache/`.
- CLI для индексации и отладки: **`python pipeline.py --help`**

---

## Тесты

```powershell
.\venv\Scripts\activate
python -m unittest tests.test_api_smoke -v
```

---

## Ограничения и ответственность

- Система **не заменяет** квалифицированного юриста; выводы нужно **проверять** по первоисточникам.
- Глобальный аудит на больших корпусах может занимать много времени и CPU.
- Качество ответов LLM зависит от выбранной модели и промптов.

---

## Критерии оценки (покрытие кейса)

- Проблема законодательной энтропии и ценность для госсектора  
- Работа с НПА: парсинг, индексация, гибридный поиск  
- Модели: NLI + LLM-объяснения  
- Explainability  
- Рабочий прототип: frontend + backend + режим быстрого теста  
- Документация: README + [docs/TECHNICAL.md](docs/TECHNICAL.md)

---

## Лицензия

MIT
