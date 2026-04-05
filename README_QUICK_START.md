# Быстрый запуск LexLens

Полная техдокументация: **[docs/TECHNICAL.md](docs/TECHNICAL.md)**.

## Требования

- Python 3.10+
- Node.js 18+

## Установка

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

```powershell
cd frontend
npm install
cd ..
```

## Старт

**Backend:**

```powershell
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**

```powershell
cd frontend
npm run dev
```

Открыть: http://localhost:5173

## Режим быстрого теста (кэш графа, быстрый UI)

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

Команда `npm run dev:demo` делает то же самое (алиас).

## AI-провайдер

Настройка через UI: http://localhost:5173/settings
