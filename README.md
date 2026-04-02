<div align="center">
  <h1>⚖️ Legal Entropy</h1>
  <p><strong>AI-система снижения энтропии законодательства Республики Казахстан</strong></p>
  <p>Автоматическое обнаружение коллизий · Дублирований · Устаревших норм</p>

  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/FAISS-CPU-FF6F00?style=for-the-badge" alt="FAISS">
  <img src="https://img.shields.io/badge/Ollama-Local-FF6F00?style=for-the-badge" alt="Ollama">
  
  <br><br>
  <strong>Для правительства и госорганов Казахстана</strong>
</div>

---

## 🎬 GIF-демонстрация

<div align="center">
  <img src="demo/legal_entropy-demo.gif" 
       alt="Legal Entropy в действии" 
       width="85%" 
       style="border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
  
  <br><br>
  <strong>LexEntropy KZ — анализ законодательства Казахстана</strong><br>
  <em>Поиск → Анализ коллизий → Граф знаний → Heatmap</em>
</div>

---

## ✨ Что уже работает (демо)

**Видео-демонстрация (3–4 минуты):**

[▶️ Смотреть полное демо](https://youtu.be/A953td1sKS8?si=sKaTIBawsh0dm1V8)  
*(Обязательно: экранка с голосом, где видно: поиск → анализ документа → обнаружение реальной коллизии → граф → heatmap → чат с объяснением)*

**Скриншоты ключевых экранов:**

![Главный поиск](screenshots/search.png)
![Анализ документа с найденной коллизией](screenshots/analyze-collision.png)
![Граф знаний НПА](screenshots/knowledge-graph.png)
![Heatmap коллизий](screenshots/heatmap.png)
![Настройки локального Ollama](screenshots/ollama-settings.png)
!Chat bot
!All the key things that we have done!

---

## 🎯 Одна фраза, которая всё меняет

**Legal-Entropy превращает хаос казахстанского законодательства в предсказуемую, прозрачную и управляемую систему.**

Система в реальном времени находит противоречия между нормами, выявляет дублирования и устаревшие статьи, строит граф связей и объясняет проблемы языком профессионального юриста.

---

## 🌟 Что такое Legal-Entropy?

**Legal-Entropy** — это производственная система интеллектуального анализа нормативно-правовых актов (НПА) Республики Казахстан. Система автоматически парсит документы с портала [Әділет](https://adilet.zan.kz), строит векторную базу знаний и запускает многоуровневый пайплайн обнаружения проблем:

```
Парсинг НПА → Чанкинг → Векторизация → Hybrid Search → NLI Детектор → LLM Объяснение
```

> **Для госсектора**: поддерживается полностью локальный режим работы через [Ollama](https://ollama.com) + Qwen — данные не покидают инфраструктуру.

---

## 🔥 Ключевые возможности

- **Гибридный поиск** (BM25 + FAISS + RRF) — максимально точный по казахстанским НПА
- **Детектор коллизий** на NLI-модели (rubert-tiny-bilingual) — O(N²) аудит всей базы
- **Граф знаний** всех связей между нормативными актами
- **Heatmap коллизий** — визуализация самых «горячих» зон законодательства
- **Семантический Diff** редакций закона с AI-резюме изменений
- **Полностью локальный режим** через Ollama + Qwen 2.5 (данные никогда не покидают сервер госоргана)
- **Мульти-провайдер AI** (Ollama / Azure OpenAI / Anthropic / OpenAI) с переключением в UI

---

## ✨ Функционал

| Модуль | Описание |
|--------|----------|
|  **Гибридный поиск** | BM25 + семантический FAISS поиск с Reciprocal Rank Fusion |
|  **Детектор коллизий** | NLI-модель (`rubert-tiny-bilingual`) для выявления противоречий O(N²) |
|  **Анализ документа** | Быстрый FAISS-анализ О(K·log N) за ~100мс без блокировки |
|  **AI Чат-помощник** | Вопросы по любому закону с контекстом из базы НПА |
|  **Граф знаний** | PyVis-визуализация связей между НПА |
|  **Heatmap коллизий** | Тепловая карта конфликтующих документов (Plotly) |
|  **Семантический Diff** | Построчное сравнение редакций НПА с AI-резюме |
|  **Локальный AI** | Qwen 2.5 / Llama через Ollama — 100% офлайн |
|  **Облачный AI** | OpenAI GPT-4o, Azure OpenAI, Anthropic Claude |
|  **Настройки через UI** | Смена провайдера, API-ключей без перезапуска сервера |

---

## 🏗️ Архитектура

```
┌──────────────────────── Frontend (React 19 + Vite) ─────────────────────────┐
│  /          Поиск НПА     /analyze/:id   Анализ документа                   │
│  /diff      Сравнение     /audit         Глобальный аудит                   │
│  /graph     Граф & Map    /index         Индексация                         │
│  /settings  AI-настройки                                                    │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │ REST API
┌─────────────────────────────▼───────────────────────────────────────────────┐
│                         FastAPI Backend (:8000)                             │
│  Routers: search · analyze · chat · audit · diff · graph · index · settings│
└───────┬─────────────────────┬───────────────────────────┬───────────────────┘
        │                     │                           │
┌───────▼──────┐   ┌──────────▼────────┐   ┌─────────────▼──────────────────┐
│ FAISS HNSW   │   │  BM25 Okapi       │   │  AI Provider                   │
│ 384-dim      │   │  rank_bm25        │   │  Ollama │ OpenAI │ Azure │ Ant  │
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
        │
┌───────▼────────────────────────────────────────────────────────────────────┐
│  data/  (gitignored)                                                       │
│  ├── parsed/        JSON-файлы НПА                                         │
│  ├── faiss/         faiss.index + bm25.pkl                                 │
│  ├── embeddings/    metadata.pkl                                            │
│  ├── cache/         nli_cache.json                                         │
│  └── ai_config.json  конфигурация провайдера                               │
└────────────────────────────────────────────────────────────────────────────┘
```

**Модели ML (работают на CPU без GPU):**
| Модель | Задача | Размер |
|--------|--------|--------|
| `intfloat/multilingual-e5-small` | Векторизация чанков | ~120 MB |
| `cointegrated/rubert-tiny-bilingual-nli` | Детекция противоречий | ~45 MB |

---

## 🚀 Быстрый старт

### Требования
- **Python** 3.10+
- **Node.js** 18+
- 4 GB RAM (8 GB рекомендуется для большой базы)

### 1. Клонировать

```bash
git clone https://github.com/your-org/baash.git
cd baash
```

### 2. Backend

```bash
# Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Установить зависимости
pip install -r requirements.txt

# Создать .env
copy .env.example .env
# Отредактируйте .env под вашего провайдера (или оставьте mock)
```

### 3. Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Запуск

**Терминал 1 — Backend API:**
```bash
uvicorn api.main:app --port 8000 --reload
```

**Терминал 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Откройте: **http://localhost:5173** 🎉

### 5. Остановка (Windows)

```powershell
taskkill /F /IM python.exe /T
taskkill /F /IM node.exe /T
```

---

## 🤖 Настройка AI-провайдера

Перейдите в **http://localhost:5173/settings** для настройки через UI — без перезапуска сервера.

### 🔒 Локальный Qwen 2.5 (рекомендуется для госсектора)

```bash
# 1. Установить Ollama
# Windows: https://ollama.com/download
# Linux:   curl -fsSL https://ollama.com/install.sh | sh

# 2. Скачать модель (~4.5 GB)
ollama pull qwen2.5:7b

# 3. Ollama стартует автоматически
```

В настройках UI: **Провайдер → Локальный (Ollama)** → Выбрать модель → Тест → Сохранить.

### ☁️ OpenAI

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 🏢 Azure OpenAI

```env
AI_PROVIDER=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

> ⚠️ **Важно**: `AZURE_OPENAI_DEPLOYMENT` — это именно **Deployment name** (не модель), созданный в Azure AI Studio.

### ⚡ Anthropic Claude

```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 📦 Уже есть папка `data/`? Используй свои данные

> Если у вас уже есть готовая база НПА (папка `data/` с ранее проиндексированными документами), **индексировать заново не нужно**. Просто скопируйте папку и запустите сервер.

### Структура папки `data/` которую нужно скопировать

```
data/
├── parsed/          ← JSON-файлы НПА (обязательно!)
│   ├── K1500000377.json
│   ├── Z1300000094.json
│   └── ...
├── faiss/           ← FAISS индекс и BM25 (обязательно для быстрого поиска!)
│   ├── faiss.index
│   └── bm25.pkl
├── embeddings/      ← Метаданные чанков (обязательно!)
│   └── metadata.pkl
├── cache/           ← NLI кэш (необязательно, ускоряет аудит)
│   └── nli_cache.json
└── models/          ← Скачанные модели HuggingFace (необязательно)
```

### Инструкция

**Шаг 1.** Скопируйте папку `data/` в корень склонированного репозитория:

```
legal-entropy/
├── api/
├── src/
├── frontend/
├── data/         ← вставьте сюда вашу папку
└── ...
```

**Шаг 2.** Проверьте что индекс валиден (необязательно):

```bash
python -c "
from src.retrieval.retriever import LegalRetriever
r = LegalRetriever()
print(f'Загружено чанков: {len(r.metadata)}')
print(f'Примеры: {[m[\"doc_id\"] for m in r.metadata[:3]]}')
"
```

**Шаг 3.** Запустите сервисы как обычно — индекс подтянется автоматически:

```bash
uvicorn api.main:app --port 8000
```

### Если у вас только `parsed/` (нет FAISS индекса)

Перестройте индекс из существующих JSON-файлов:

```bash
curl -X POST http://localhost:8000/api/v1/index/rebuild
```

Или через Python напрямую:

```bash
python -c "
from src.retrieval.retriever import LegalRetriever
r = LegalRetriever()
added = r.rebuild_index()
print(f'Проиндексировано: {added} чанков')
"
```

> ⏱️ Перестройка индекса на 25 000 чанков занимает ~5-10 минут (однократно).  
> После этого сервер стартует мгновенно при каждом следующем запуске.

---

## 📚 Индексация НПА (с нуля)

### Через UI

1. Перейдите в **Индексация НПА** (`/index`)
2. Введите ID документа с Аdilet (например: `K1500000377`)
3. Нажмите `--build-index`

### Через API

```bash
curl -X POST http://localhost:8000/api/v1/index/build \
  -H "Content-Type: application/json" \
  -d '{"doc_ids": ["K1500000377", "K1400000266", "Z1300000094"]}'
```

Формат ID: код документа из URL `adilet.zan.kz/rus/docs/**K1500000377**`

## 📡 API Reference

Swagger UI: **http://localhost:8000/docs**

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/search` | `POST` | Гибридный BM25+FAISS поиск |
| `/api/v1/analyze/{doc_id}` | `GET` | Быстрый анализ документа |
| `/api/v1/chat` | `POST` | AI-чат с контекстом из НПА |
| `/api/v1/audit/detect` | `POST` | Полный O(N²) NLI-аудит базы |
| `/api/v1/diff` | `POST` | Семантический diff двух текстов |
| `/api/v1/graph/html` | `GET` | Граф знаний (PyVis HTML) |
| `/api/v1/graph/heatmap` | `GET` | Heatmap коллизий (Plotly JSON) |
| `/api/v1/index/build` | `POST` | Парсинг и индексация НПА |
| `/api/v1/settings/ai` | `GET/POST` | Конфигурация AI-провайдера |
| `/api/v1/settings/ai/test` | `POST` | Тест соединения с провайдером |
| `/api/v1/settings/ollama/models` | `GET` | Список доступных Ollama-моделей |
| `/health` | `GET` | Статус сервера |

### Пример поиска

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "штраф за нарушение экологических норм", "top_k": 5}'
```

---

## 📂 Структура проекта

```
baash/
├── api/                          # FastAPI backend
│   ├── main.py                   # Точка входа, CORS, middleware
│   ├── models/schemas.py         # Pydantic модели (Issue, SearchResult, ...)
│   ├── routers/
│   │   ├── analyze.py            # GET  /analyze/{doc_id}
│   │   ├── audit.py              # POST /audit/detect  ← ThreadPool
│   │   ├── chat.py               # POST /chat
│   │   ├── diff.py               # POST /diff
│   │   ├── graph.py              # GET  /graph/html|heatmap
│   │   ├── index.py              # POST /index/build
│   │   ├── search.py             # POST /search
│   │   └── settings.py           # GET/POST /settings/ai
│   └── services/
│       ├── ai_provider.py        # Мульти-провайдер: Azure/OpenAI/Ollama/Anthropic
│       └── nlp_service.py        # NLP сервис — поиск, анализ документа
│
├── src/                          # Core ML/NLP pipeline
│   ├── embeddings/
│   │   └── embedder.py           # Sentence-Transformers e5-small
│   ├── retrieval/
│   │   └── retriever.py          # FAISS HNSW + BM25 + RRF Fusion
│   ├── reasoning/
│   │   ├── detector.py           # O(N²) NLI collision audit
│   │   ├── nli.py                # NLI batch inference + disk cache
│   │   ├── explainer.py          # LLM JSON explanation (все провайдеры)
│   │   ├── version_compare.py    # Semantic diff чанков
│   │   └── deduplicator.py       # Дедупликация базы
│   ├── graph/
│   │   └── knowledge_graph.py    # PyVis граф + Plotly heatmap
│   └── scraper/
│       └── adilet_scraper.py     # Парсер adilet.zan.kz
│
├── frontend/                     # React 19 + Vite 6 + TailwindCSS 3
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Search.tsx        # Главная: гибридный поиск
│   │   │   ├── Analyze.tsx       # Анализ НПА
│   │   │   ├── Diff.tsx          # Сравнение версий
│   │   │   ├── GlobalAudit.tsx   # Глобальный аудит O(N)
│   │   │   ├── GraphNetwork.tsx  # Граф & Heatmap
│   │   │   ├── IndexDocs.tsx     # Индексация документов
│   │   │   └── Settings.tsx      # Настройки AI-провайдера
│   │   ├── components/
│   │   │   ├── NavSidebar.tsx    # Floating glassmorphism navigation
│   │   │   └── Sidebar.tsx       # AI Chat panel
│   │   ├── services/api.ts       # Axios клиент (раздельные таймауты)
│   │   └── store/useStore.ts     # Zustand global state
│   ├── public/
│   │   └── night_bg.png          # Фон "ночное небо"
│   └── package.json
│
├── data/                         # (gitignored) Данные и индексы
│   ├── parsed/                   # JSON-файлы НПА
│   ├── faiss/                    # FAISS индекс + BM25
│   ├── embeddings/               # Метаданные чанков
│   ├── cache/                    # NLI кэш (nli_cache.json)
│   ├── models/                   # Скачанные HuggingFace модели
│   └── ai_config.json            # Динамические настройки AI (через UI)
│
├── .env.example                  # Пример конфигурации
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Конфигурация (.env)

```env
# === AI Provider ===
# Варианты: azure | openai | anthropic | ollama | mock
AI_PROVIDER=mock

# === Azure OpenAI ===
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o          # Deployment Name из Azure AI Studio

# === OpenAI ===
OPENAI_API_KEY=

# === Anthropic ===
ANTHROPIC_API_KEY=

# === Ollama (локальный) ===
# Ollama запускается автоматически, никакого ключа не нужно
# Модель выбирается в UI /settings
```

> 💡 После сохранения настроек через UI (`/settings`) конфиг записывается в `data/ai_config.json` и применяется сразу — сервер перезапускать не нужно.

---

## 🔐 Безопасность для госсектора

LexEntropy поддерживает **полностью изолированный** режим работы:

1. **Локальный AI** — Ollama + Qwen 2.5:7b, данные не выходят за пределы сервера
2. **Офлайн-модели** — e5-small и rubert-tiny скачиваются один раз в `data/models/`
3. **Нет внешних запросов** — при `AI_PROVIDER=ollama` все вызовы идут на `localhost:11434`
4. **API ключи не в коде** — хранятся в `.env` (не коммитится) и `data/ai_config.json`

---

## 🧪 Производительность

| Операция | Время | Примечание |
|----------|-------|------------|
| Гибридный поиск | ~150–400 мс | BM25 + FAISS + RRF, 25k чанков |
| Анализ документа | ~100–500 мс | FAISS-only, без NLI |
| Полный аудит O(N²) | 5–30 мин | NLI на 28k пар, с кэшем быстрее |
| AI-чат (Ollama q4) | 2–8 сек | Qwen2.5:7b на CPU |
| AI-чат (GPT-4o) | 0.5–2 сек | Через API |
| Индексация 1 НПА | 3–15 сек | Парсинг + e5-small эмбеддинг |

---

## 🛠️ Стек технологий

| Уровень | Технологии |
|---------|-----------|
| **Frontend** | React 19, Vite 6, TailwindCSS 3, Zustand, Axios, Lucide, React-Plotly, PyVis (iframe) |
| **Backend** | FastAPI, Uvicorn, Pydantic v2 |
| **Search** | FAISS (IndexHNSWFlat, CPU), rank-bm25, Sentence-Transformers |
| **NLP** | HuggingFace Transformers, intfloat/multilingual-e5-small, cointegrated/rubert-tiny-bilingual-nli |
| **AI** | OpenAI SDK, Anthropic SDK, httpx (Ollama) |
| **Visualization** | PyVis (граф), Plotly (heatmap) |
| **Data** | JSON (parsed), Pickle (FAISS/BM25 индексы) |

---

## 📄 Лицензия

MIT License — свободное использование, включая коммерческое.

---

## 📬 Связь

Проект разработан для анализа законодательства **Республики Казахстан**.  
База НПА: [Әділет — Информационно-правовая система](https://adilet.zan.kz)

---

## 👥 Команда

**LexEntropy** создали:

| Фото | Имя | Роль |
|------|-----|------|
| ![Shyngyskhan](https://github.com/Shyngyskhan-333) | **Shyngyskhan** |
| ![Arsen](https://github.com/Arseniiiii-ai) | **Arsen** |
| ![Baktyar](https://github.com/sronters) | **Baktyar** |
| ![Arnur](https://github.com/arnurmakhmutzhan-eng) | **Arnur** |

<div align="center">
<sub>Built with ⚖️ for Kazakhstan Legal Tech</sub>
</div>
