from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass

from src.evidence.models import SourceSnapshot, compute_sha256

PARSE_QUALITY_METADATA_ONLY = "metadata_only"
PARSE_QUALITY_STRUCTURED_LEGAL_TEXT = "structured_legal_text"
PARSER_VERSION = "source-parser-v1"


@dataclass(frozen=True, slots=True)
class ParsedSourceDocument:
    source_snapshot_id: str
    doc_id: str
    title: str
    url: str
    date: str
    parse_quality: str
    parser_version: str
    legal_text_available: bool
    articles: tuple[dict, ...]
    references: tuple[str, ...]


class SourceParser:
    """Pure parser boundary: derives metadata from raw content without creating evidence objects."""

    def parse(self, *, snapshot: SourceSnapshot, raw_content: str | bytes) -> ParsedSourceDocument:
        _require_matching_snapshot(snapshot, raw_content)
        text = _to_text(raw_content)
        doc_id = _doc_id_from_url(snapshot.url)
        articles = _extract_articles(text)
        legal_text_available = bool(articles)
        return ParsedSourceDocument(
            source_snapshot_id=snapshot.id,
            doc_id=doc_id,
            title=_extract_title(text) or doc_id,
            url=snapshot.url,
            date=_extract_date(text),
            parse_quality=PARSE_QUALITY_STRUCTURED_LEGAL_TEXT if legal_text_available else PARSE_QUALITY_METADATA_ONLY,
            parser_version=PARSER_VERSION,
            legal_text_available=legal_text_available,
            articles=articles,
            references=_extract_references(text),
        )


def _require_matching_snapshot(snapshot: SourceSnapshot, raw_content: str | bytes) -> None:
    if compute_sha256(raw_content) != snapshot.content_hash:
        raise ValueError("raw_content hash does not match source snapshot")


def _to_text(raw_content: str | bytes) -> str:
    if isinstance(raw_content, bytes):
        return raw_content.decode("utf-8", errors="replace")
    return raw_content


def _doc_id_from_url(url: str) -> str:
    match = re.search(r"/docs/([^/?#]+)", url, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return url.rstrip("/").rsplit("/", 1)[-1] or "unknown"


def _extract_title(raw_content: str) -> str:
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", raw_content, re.IGNORECASE | re.DOTALL)
    if not title_match:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_content, re.IGNORECASE | re.DOTALL)
    if not title_match:
        return ""
    raw_title = re.sub(r"<[^>]+>", " ", title_match.group(1))
    return re.sub(r"\s+", " ", html_lib.unescape(raw_title)).strip()


def _extract_date(raw_content: str) -> str:
    match = re.search(r"\d{2}\.\d{2}\.\d{4}", raw_content)
    return match.group(0) if match else ""


def _extract_references(raw_content: str) -> tuple[str, ...]:
    references = sorted(set(re.findall(r"/rus/docs/([A-Z]\d+_?)", raw_content, re.IGNORECASE)))
    return tuple(reference.upper() for reference in references)


def _extract_articles(raw_content: str) -> tuple[dict, ...]:
    articles: list[dict] = []
    for order, match in enumerate(_iter_article_blocks(raw_content), start=1):
        attrs = match.group("attrs")
        body = match.group("body")
        number = _extract_article_number(attrs, body) or str(order)
        heading = _extract_heading(body)
        title = _extract_article_title(heading, number)
        paragraphs = tuple(_extract_paragraphs(body))
        article_text = "\n".join(paragraphs)
        if not article_text:
            continue
        articles.append(
            {
                "number": number,
                "title": title,
                "text": article_text,
                "order": order,
                "clauses": _extract_clauses(number, paragraphs),
            }
        )
    return tuple(articles)


def _iter_article_blocks(raw_content: str):
    block_pattern = re.compile(
        r"<(?P<tag>section|article|div)\b(?P<attrs>[^>]*)>(?P<body>.*?)</(?P=tag)>",
        re.IGNORECASE | re.DOTALL,
    )
    for match in block_pattern.finditer(raw_content):
        attrs = match.group("attrs")
        if re.search(r"\bclass\s*=\s*['\"][^'\"]*\barticle\b", attrs, re.IGNORECASE) or re.search(
            r"\bdata-article-number\s*=", attrs, re.IGNORECASE
        ):
            yield match


def _extract_article_number(attrs: str, body: str) -> str:
    attr_match = re.search(r"\bdata-article-number\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.IGNORECASE)
    if attr_match:
        return _clean_text(attr_match.group(1))
    heading = _extract_heading(body)
    heading_match = re.search(r"Статья\s+([0-9A-Za-zА-Яа-я.-]+)", heading, re.IGNORECASE)
    return _clean_text(heading_match.group(1)) if heading_match else ""


def _extract_heading(body: str) -> str:
    heading_match = re.search(r"<h[1-6][^>]*>(.*?)</h[1-6]>", body, re.IGNORECASE | re.DOTALL)
    return _clean_html_text(heading_match.group(1)) if heading_match else ""


def _extract_article_title(heading: str, number: str) -> str:
    if not heading:
        return ""
    title = re.sub(rf"^\s*Статья\s+{re.escape(number)}\.?\s*", "", heading, flags=re.IGNORECASE).strip()
    return title


def _extract_paragraphs(body: str) -> list[str]:
    paragraphs: list[str] = []
    for paragraph_match in re.finditer(r"<p[^>]*>(.*?)</p>", body, re.IGNORECASE | re.DOTALL):
        paragraph = _clean_html_text(paragraph_match.group(1))
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def _extract_clauses(article_number: str, paragraphs: tuple[str, ...]) -> tuple[dict, ...]:
    clauses: list[dict] = []
    for order, paragraph in enumerate(paragraphs, start=1):
        clause_number: str | None = None
        clause_text = paragraph
        number_match = re.match(r"^(\d+)\.\s+(.*)$", paragraph, re.DOTALL)
        if number_match:
            clause_number = number_match.group(1)
            clause_text = number_match.group(2).strip()
        clauses.append(
            {
                "number": clause_number,
                "path": f"article:{article_number}/clause:{order}",
                "text": clause_text,
                "order": order,
            }
        )
    return tuple(clauses)


def _clean_html_text(value: str) -> str:
    return _clean_text(re.sub(r"<[^>]+>", " ", value))


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(value)).strip()
