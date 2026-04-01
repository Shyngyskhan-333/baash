from fastapi import APIRouter, HTTPException
from typing import List
import difflib

from api.models.schemas import DiffRequest, DiffResponse, DiffHunk, DiffStats
from api.services.nlp_service import nlp_service
from api.services.ai_provider import ai_provider

router = APIRouter()


def _text_to_lines(text: str) -> List[str]:
    """Split text into lines, treating both newlines and sentences as units."""
    import re
    lines = re.split(r"(?<=[.!?;])\s+|\n+", text.strip())
    return [l.strip() for l in lines if l.strip()]


def _compute_hunks(text_a: str, text_b: str) -> tuple:
    """
    Real line-by-line diff using difflib, returning (hunks, stats).
    """
    lines_a = _text_to_lines(text_a)
    lines_b = _text_to_lines(text_b)

    matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
    opcodes = matcher.get_opcodes()

    hunks: List[DiffHunk] = []
    added = removed = changed = 0

    for line_num, (tag, i1, i2, j1, j2) in enumerate(opcodes, start=1):
        old = " ".join(lines_a[i1:i2]) if i2 > i1 else None
        new = " ".join(lines_b[j1:j2]) if j2 > j1 else None

        if tag == "equal":
            hunks.append(DiffHunk(type="unchanged", old_text=old, new_text=new, line_number=line_num))
        elif tag == "replace":
            hunks.append(DiffHunk(type="changed", old_text=old, new_text=new, line_number=line_num))
            changed += 1
        elif tag == "insert":
            hunks.append(DiffHunk(type="added", old_text=None, new_text=new, line_number=line_num))
            added += 1
        elif tag == "delete":
            hunks.append(DiffHunk(type="removed", old_text=old, new_text=None, line_number=line_num))
            removed += 1

    return hunks, DiffStats(added=added, removed=removed, changed=changed)


def _extract_doc_text(doc: dict) -> str:
    """Extract full text from a parsed JSON document."""
    parts = []
    for art in doc.get("articles", []):
        # Try direct text field first, then chunks
        if art.get("text"):
            parts.append(art["text"])
        else:
            for chunk in art.get("chunks", []):
                parts.append(chunk.get("text", ""))
    return "\n".join(parts)


@router.post("/api/v1/diff", response_model=DiffResponse)
async def diff_documents(request: DiffRequest):
    """
    Сравнение двух версий документа или произвольных текстов.
    Возвращает построчный diff с реальными изменениями.
    """
    text_a = request.text_a or ""
    text_b = request.text_b or ""

    # Fetch documents by version IDs if provided
    if request.doc_id and request.version_a and request.version_b:
        doc_a = nlp_service.get_document_by_id(f"{request.doc_id}_{request.version_a}")
        doc_b = nlp_service.get_document_by_id(f"{request.doc_id}_{request.version_b}")
        if doc_a:
            text_a = _extract_doc_text(doc_a)
        if doc_b:
            text_b = _extract_doc_text(doc_b)

    if not text_a.strip() and not text_b.strip():
        raise HTTPException(status_code=400, detail="Укажите тексты для сравнения (text_a и text_b)")

    # Compute real line-by-line diff
    hunks, stats = _compute_hunks(text_a, text_b)

    # AI summary of changes
    try:
        change_summary = f"Добавлено: {stats.added}, удалено: {stats.removed}, изменено: {stats.changed} фрагментов."
        ai_summary = await ai_provider.complete(
            messages=[{
                "role": "user",
                "content": (
                    f"Сравни две редакции нормативного текста и объясни суть изменений.\n\n"
                    f"СТАРАЯ РЕДАКЦИЯ:\n{text_a[:800]}\n\n"
                    f"НОВАЯ РЕДАКЦИЯ:\n{text_b[:800]}\n\n"
                    f"Статистика diff: {change_summary}\n\n"
                    f"Дай краткое юридическое заключение (3-4 предложения) об изменениях."
                )
            }],
            system_prompt="Ты AI-юрист, специализирующийся на анализе изменений в законодательстве Казахстана."
        )
    except Exception:
        ai_summary = f"AI недоступен. {change_summary}"

    return DiffResponse(hunks=hunks, stats=stats, ai_summary=ai_summary)
