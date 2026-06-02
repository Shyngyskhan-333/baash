from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.evidence.models import SourceSnapshot


@dataclass(frozen=True, slots=True)
class FetchedSourceContent:
    source_id: str
    url: str
    content: str | bytes
    raw_content_uri: str
    fetched_at: datetime | None = None
    http_status: int | None = None
    fetch_method: str = "http"

    def __post_init__(self) -> None:
        _require(self.source_id, "source_id")
        _require(self.url, "url")
        _require(self.raw_content_uri, "raw_content_uri")


class SourceSnapshotBuilder:
    """Creates source snapshots from fetched raw content before parsing starts."""

    def build(self, fetched: FetchedSourceContent) -> SourceSnapshot:
        if _content_length(fetched.content) == 0:
            raise ValueError("content is required")
        return SourceSnapshot.from_content(
            source_id=fetched.source_id,
            url=fetched.url,
            content=fetched.content,
            raw_content_uri=fetched.raw_content_uri,
            fetched_at=fetched.fetched_at,
            http_status=fetched.http_status,
            parser_version=None,
            fetch_method=fetched.fetch_method,
        )

    def build_and_store(self, fetched: FetchedSourceContent) -> SourceSnapshot:
        _write_raw_content(fetched.raw_content_uri, fetched.content)
        return self.build(fetched)


def _write_raw_content(raw_content_uri: str, content: str | bytes) -> None:
    path = Path(raw_content_uri)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
        return
    path.write_text(content, encoding="utf-8")


def _content_length(content: str | bytes) -> int:
    if isinstance(content, bytes):
        return len(content)
    return len(content.strip())


def _require(value: str, field_name: str) -> str:
    if not str(value).strip():
        raise ValueError(f"{field_name} is required")
    return str(value).strip()
