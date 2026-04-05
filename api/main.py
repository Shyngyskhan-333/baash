from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

env_file = os.getenv("ENV_FILE", ".env").strip() or ".env"
load_dotenv(dotenv_path=Path(env_file))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(
    title="LexLens AI API",
    description="API для анализа законодательства Казахстана (NLP, RAG, LLM).",
    version="1.0.0"
)

cors_origins_env = os.getenv("CORS_ORIGINS", "")
origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] or [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

from api.routers import search, analyze, chat, diff, index, audit, graph, settings, precompute

app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analyze"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(diff.router, prefix="/api/v1", tags=["Diff"])
app.include_router(index.router, prefix="/api/v1", tags=["Index"])
app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
app.include_router(graph.router, prefix="/api/v1", tags=["Graph"])
app.include_router(settings.router, prefix="/api/v1", tags=["Settings"])
app.include_router(precompute.router, prefix="/api/v1", tags=["Precompute"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "LexLens API is running"}

@app.options("/{full_path:path}")
async def options_fallback(full_path: str):

    return Response(status_code=204)