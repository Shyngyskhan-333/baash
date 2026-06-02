"""Citation-aware search boundary for LexLens V2."""

from src.search.canonical_grounding import CanonicalSearchGroundingService
from src.search.canonical_service import CanonicalSearchService
from src.search.canonical_retrieval import InMemoryCanonicalRetrievalIndex
from src.search.result_formatter import CanonicalSearchResultFormatter
from src.search.service import SearchService

__all__ = [
    "CanonicalSearchGroundingService",
    "CanonicalSearchResultFormatter",
    "CanonicalSearchService",
    "InMemoryCanonicalRetrievalIndex",
    "SearchService",
]
