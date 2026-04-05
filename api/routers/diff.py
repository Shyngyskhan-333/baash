import asyncio
import difflib
import re
from typing import List

from fastapi import APIRouter, HTTPException

from api.models.schemas import DiffHunk, DiffRequest, DiffResponse, DiffStats
from api.services.ai_provider import ai_provider
from api.services.nlp_service import nlp_service

router = APIRouter()


def _text_to_lines(text: str) -> List[str]:
    lines = re.split(r"(?<=[.!?;])\s+|\n+", text.strip())
    return [line.strip() for line in lines if line.strip()]


def _compute_hunks(text_a: str, text_b: str):
    lines_a = _text_to_lines(text_a)
    lines_b = _text_to_lines(text_b)
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)

    hunks: List[DiffHunk] = []
    added = 0
    removed = 0
    changed = 0

    for line_number, (tag, i1, i2, j1, j2) in enumerate(matcher.get_opcodes(), start=1):
        old_text = " ".join(lines_a[i1:i2]) if i2 > i1 else None
        new_text = " ".join(lines_b[j1:j2]) if j2 > j1 else None

        if tag == "equal":
            hunks.append(DiffHunk(type="unchanged", old_text=old_text, new_text=new_text, line_number=line_number))
        elif tag == "replace":
            hunks.append(DiffHunk(type="changed", old_text=old_text, new_text=new_text, line_number=line_number))
            changed += 1
        elif tag == "insert":
            hunks.append(DiffHunk(type="added", old_text=None, new_text=new_text, line_number=line_number))
            added += 1
        elif tag == "delete":
            hunks.append(DiffHunk(type="removed", old_text=old_text, new_text=None, line_number=line_number))
            removed += 1

    return hunks, DiffStats(added=added, removed=removed, changed=changed)


def _extract_doc_text(document: dict) -> str:
    parts: List[str] = []
    for article in document.get("articles", []):
        if article.get("text"):
            parts.append(article["text"])
            continue

        for chunk in article.get("chunks", []):
            parts.append(chunk.get("text", ""))

    return "\n".join(parts)


async def _build_ai_summary(text_a: str, text_b: str, stats: DiffStats) -> str:
    change_summary = f"Добавлено: {stats.added}, удалено: {stats.removed}, изменено: {stats.changed} фрагментов."

    try:
        return await asyncio.wait_for(
            ai_provider.complete(
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Сравни две редакции нормативного текста и объясни суть изменений.\n\n"
                            f"СТАРАЯ РЕДАКЦИЯ:\n{text_a[:3000]}\n\n"
                            f"НОВАЯ РЕДАКЦИЯ:\n{text_b[:3000]}\n\n"
                            f"Статистика diff: {change_summary}\n\n"
                            "Дай краткое юридическое заключение в 3-4 предложениях об изменениях."
                        ),
                    }
                ],
                system_prompt="Ты AI-юрист, который кратко и ясно объясняет изменения в законодательных редакциях.",
            ),
            timeout=12,
        )
    except Exception:
        return f"AI недоступен. {change_summary}"


@router.post("/diff", response_model=DiffResponse)
async def diff_documents(request: DiffRequest):
    text_a = request.text_a or ""
    text_b = request.text_b or ""

    if request.doc_id and request.version_a and request.version_b:
        def parsed_stem(base_doc_id: str, version_key: str) -> str:
            if not version_key or version_key == base_doc_id:
                return base_doc_id
            if version_key.startswith(base_doc_id + "_"):
                return version_key
            return f"{base_doc_id}_{version_key}"

        doc_a = nlp_service.get_document_by_id(parsed_stem(request.doc_id, request.version_a))
        doc_b = nlp_service.get_document_by_id(parsed_stem(request.doc_id, request.version_b))

        if doc_a:
            text_a = _extract_doc_text(doc_a)
        if doc_b:
            text_b = _extract_doc_text(doc_b)

    if not text_a.strip() and not text_b.strip():
        raise HTTPException(status_code=400, detail="Укажите тексты для сравнения.")

    hunks, stats = _compute_hunks(text_a, text_b)
    ai_summary = await _build_ai_summary(text_a, text_b, stats)

    return DiffResponse(hunks=hunks, stats=stats, ai_summary=ai_summary)