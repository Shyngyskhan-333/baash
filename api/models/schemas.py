from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

# --- Common Schemas ---

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

# --- Search API ---

class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None
    doc_ids: Optional[List[str]] = None

class SearchResult(BaseModel):
    doc_id: str
    title: str
    excerpt: str
    text: Optional[str] = None
    score: float
    bm25_score: Optional[float] = 0.0
    cosine_score: Optional[float] = 0.0
    risk_level: Literal["low", "medium", "high"]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query_vector: Optional[List[float]] = None

# --- Analyze API ---

class Issue(BaseModel):
    type: Literal["contradiction", "collision", "duplicate", "outdated"]
    article: str
    description: str
    severity: Literal["low", "medium", "high"]
    related_doc_id: Optional[str] = None
    explanation: Optional[str] = None # Added per requirements

class RelatedLaw(BaseModel):
    doc_id: str
    title: str
    relevance_score: float

class AnalyzeResponse(BaseModel):
    doc_id: str
    title: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]
    issues: List[Issue]
    summary: str
    reasoning: Optional[str] = None
    related_laws: List[RelatedLaw]


# --- Diff API ---

class DiffRequest(BaseModel):
    doc_id: Optional[str] = None
    version_a: Optional[str] = None
    version_b: Optional[str] = None
    text_a: Optional[str] = None
    text_b: Optional[str] = None

class DiffHunk(BaseModel):
    type: Literal["added", "removed", "changed", "unchanged"]
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    line_number: int
    article: Optional[str] = None

class DiffStats(BaseModel):
    added: int
    removed: int
    changed: int

class DiffResponse(BaseModel):
    hunks: List[DiffHunk]
    stats: DiffStats
    ai_summary: str

# --- Chat API ---

class ChatRequest(BaseModel):
    message: str
    doc_id: Optional[str] = None # For specific article lookup
    doc_ids: Optional[List[str]] = None # GLOBAL SCOPE (Active Workspace)
    history: List[Message] = []
    mode: Literal["general", "article_search"] = "general"

class Source(BaseModel):
    article: str
    text: str
    relevance: float

class SuggestedArticle(BaseModel):
    doc_id: str
    article: str
    title: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    suggested_articles: Optional[List[SuggestedArticle]] = []
    explanation: Optional[str] = None # Why this answer
