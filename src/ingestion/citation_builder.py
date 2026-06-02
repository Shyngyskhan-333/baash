from __future__ import annotations

from dataclasses import dataclass

from src.evidence.models import Article, Citation, Clause, make_stable_id
from src.ingestion.parser import ParsedSourceDocument


@dataclass(frozen=True, slots=True)
class ParsedCitationBundle:
    articles: tuple[Article, ...]
    clauses: tuple[Clause, ...]
    citations: tuple[Citation, ...]


class ParsedCitationBuilder:
    """Converts parsed legal structure into immutable evidence objects."""

    def build(
        self,
        *,
        parsed: ParsedSourceDocument,
        document_version_id: str,
        citation_title: str | None = None,
    ) -> ParsedCitationBundle:
        if not parsed.legal_text_available or not parsed.articles:
            raise ValueError("parsed document does not contain citable legal text")

        articles: list[Article] = []
        clauses: list[Clause] = []
        citations: list[Citation] = []
        title = citation_title or parsed.title

        for raw_article in parsed.articles:
            article = _build_article(raw_article, document_version_id)
            articles.append(article)
            for raw_clause in raw_article.get("clauses", ()):
                clause = _build_clause(raw_clause, article)
                citation = _build_citation(
                    raw_clause=raw_clause,
                    article=article,
                    clause=clause,
                    document_version_id=document_version_id,
                    citation_title=title,
                )
                clauses.append(clause)
                citations.append(citation)

        if not citations:
            raise ValueError("parsed document does not contain citable clauses")

        return ParsedCitationBundle(
            articles=tuple(articles),
            clauses=tuple(clauses),
            citations=tuple(citations),
        )


def _build_article(raw_article: dict, document_version_id: str) -> Article:
    number = str(raw_article["number"])
    text = str(raw_article["text"])
    article_id = make_stable_id("article", document_version_id, number, text)
    return Article.from_text(
        id=article_id,
        document_version_id=document_version_id,
        number=number,
        text=text,
        title=raw_article.get("title") or None,
        order=int(raw_article.get("order") or 0),
    )


def _build_clause(raw_clause: dict, article: Article) -> Clause:
    path = str(raw_clause["path"])
    text = str(raw_clause["text"])
    clause_id = make_stable_id("clause", article.id, path, text)
    number = raw_clause.get("number")
    return Clause.from_text(
        id=clause_id,
        article_id=article.id,
        path=path,
        text=text,
        number=str(number) if number is not None else None,
        order=int(raw_clause.get("order") or 0),
    )


def _build_citation(
    *,
    raw_clause: dict,
    article: Article,
    clause: Clause,
    document_version_id: str,
    citation_title: str,
) -> Citation:
    start_offset = article.text.find(clause.text)
    if start_offset < 0:
        start_offset = None
        end_offset = None
    else:
        end_offset = start_offset + len(clause.text)
    clause_label = clause.number or str(raw_clause.get("order") or clause.order)
    citation_id = make_stable_id("citation", document_version_id, article.id, clause.id, clause.text)
    return Citation(
        id=citation_id,
        document_version_id=document_version_id,
        article_id=article.id,
        clause_id=clause.id,
        quote=clause.text,
        citation_label=f"{citation_title}, Article {article.number}, Clause {clause_label}",
        start_offset=start_offset,
        end_offset=end_offset,
    )
