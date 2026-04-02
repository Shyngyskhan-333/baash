from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

# Set up simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# Create FastAPI app
app = FastAPI(
    title="LexEntropy AI API",
    description="API для аудита законодательства Казахстана на базе NLP & LLM.",
    version="1.0.0"
)

# Configure CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Log Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Error handling is handled globally by FastAPI internally for 500s and 422s

# Import and include routers
from api.routers import search, analyze, chat, diff, index, audit, graph

app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analyze"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(diff.router, prefix="/api/v1", tags=["Diff"])
app.include_router(index.router, prefix="/api/v1", tags=["Index"])
app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])
app.include_router(graph.router, prefix="/api/v1", tags=["Graph"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "LexEntropy API is running"}
