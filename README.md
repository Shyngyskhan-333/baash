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

<img width="1280" height="728" alt="image" src="https://github.com/user-attachments/assets/6bfa005b-5848-4fba-ae54-d8dc5b42b989" />

<img width="1280" height="726" alt="image" src="https://github.com/user-attachments/assets/93601000-afb7-4975-969d-80c8cc99f4a4" />

<img width="285" height="950" alt="image" src="https://github.com/user-attachments/assets/988a29e8-28e5-4d1b-a6bb-0273fd340107" />

<img width="279" height="540" alt="image" src="https://github.com/user-attachments/assets/240950d0-4772-4b49-9382-cdcde1aa125a" />

---

## Демо


[Смотреть полное демо](https://youtu.be/an1OuracBYk)  

---

## Что такое LexLens?

**LexLens** — это производственная система интеллектуального анализа НПА РК. Система автоматически парсит документы с портала [Әділет](https://adilet.zan.kz), строит векторную базу знаний и запускает многоуровневый пайплайн обнаружения проблем:

```
Парсинг НПА → Чанкинг → Векторизация → Hybrid Search → NLI Детектор → LLM Объяснение
```

> **Провайдеры**: Поддерживается Azure OpenAI Compatible и полностью локальный Ollama

---

## Функционал

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
|  **Облачный AI** | Azure OpenAI|
|  **Настройки через UI** | Смена провайдера, API-ключей без перезапуска сервера |

---

## Архитектура

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
| `intfloat/multilingual-e5-small` | Векторизация чанков | ~120 MB |
| `cointegrated/rubert-tiny-bilingual-nli` | Детекция противоречий | ~45 MB |

---

## Быстрый старт

### Требования
- **Python** 3.10+
- **Node.js** 18+
- 4 GB RAM

### 1. Клонировать

```bash
git clone https://github.com/Shyngyskhan-333/lexlens.git
cd lexlens
```

### 2. Backend

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# Отредактируйте .env.example под вашего провайдера

copy .env.example .env

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

Откройте: **http://localhost:5173**
---

---

## Установка и запуск расширения (Unpacked)

Движок: Chromium (Google Chrome, Microsoft Edge, Brave).

### 1. Подготовка исходников
Склонировать:
```bash
git clone https://github.com/Shyngyskhan-333/lexlens.git
cd lexlens
```
### 2. Подключение
- Перейдите в раздел расширений
- Включите Режим разработчика
- Нажмите кнопку **Загрузить распакованное расширение**
- Выберите папку /extension с корневой папки LexLens

---

## Настройка AI-провайдера

Перейдите в **http://localhost:5173/settings** для настройки через UI — без перезапуска сервера.

### Локальный Qwen 2.5 (рекомендуется для госсектора)

```bash
# 1. Установить Ollama
# Windows: https://ollama.com/download
# Linux:   curl -fsSL https://ollama.com/install.sh | sh

# 2. Скачать модель (~4.5 GB)
ollama pull qwen2.5:7b

# 3. Ollama стартует автоматически
```

В настройках UI: **Провайдер → Локальный (Ollama)** → Выбрать модель → Тест → Сохранить.

### Azure OpenAI

```env
AI_PROVIDER=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

> ⚠️ **Важно**: `AZURE_OPENAI_DEPLOYMENT` — это именно **Deployment name** (не модель), созданный в Azure AI Studio.

## Уже есть папка `data/`?

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
lexlens/
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

> ⏱️ Перестройка индекса на 25 000 чанков занимает ~5-10 минут (однократно).  
> После этого сервер стартует мгновенно при каждом следующем запуске.

---

## Индексация НПА (с нуля)

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

Формат ID: код документа из URL `adilet.zan.kz/rus/docs/-> K1500000377 <-`

---

## Безопасность для госсектора

LexEntropy поддерживает **полностью изолированный** режим работы:

1. **Локальный AI** — Ollama + Qwen 2.5:7b, данные не выходят за пределы сервера
2. **Офлайн-модели** — e5-small и rubert-tiny скачиваются один раз в `data/models/`
3. **Нет внешних запросов** — при `AI_PROVIDER=ollama` все вызовы идут на `localhost:11434`
4. **API ключи не в коде** — хранятся в `.env` (не коммитится) и `data/ai_config.json`

---
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

---

## Связь

Проект разработан для анализа законодательства **Республики Казахстан**.  
База НПА: [Әділет — Информационно-правовая система](https://adilet.zan.kz)

---

### Команда

**LexLens** создали:

<table>
<tr>
<th>GitHub</th>
<th>Имя</th>
</tr>

<tr>
<td>
<a href="https://github.com/sronters">
<img src="https://github.com/sronters.png" width="60">
</a>
</td>
<td>Baktiyar</td>
</tr>

<tr>
<td>
<a href="https://github.com/Arseniiiii-ai">
<img src="https://github.com/Arseniiiii-ai.png" width="60">
</a>
</td>
<td>Arsen</td>
</tr>

<tr>
<td>
<a href="https://github.com/arnurmakhmutzhan-eng">
<img src="https://github.com/arnurmakhmutzhan-eng.png" width="60">
</a>
</td>
<td>Arnur</td>
</tr>

<tr>
<td>
<a href="https://github.com/Shyngyskhan-333">
<img src="https://github.com/Shyngyskhan-333.png" width="60">
</a>
</td>
<td>SHyngyskhan</td>
</tr>

</table>

<div align="center">
<sub>Built by BAASH for Kazakhstan Legal Tech</sub>
</div>
