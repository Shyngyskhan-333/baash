"""
Сравнение двух редакций закона (Semantic Diff) с автоматической HTML-подсветкой.
Использует intfloat/multilingual-e5-small для сравнения чанков по смыслу.
"""
import difflib
from typing import Dict, List

import numpy as np

from src.embeddings.embedder import embed_text


def highlight_text_diff(text_old: str, text_new: str) -> str:
    """Генерирует HTML с подсветкой (красный для удаленного, зеленый для нового)."""
    matcher = difflib.SequenceMatcher(None, text_old.split(), text_new.split())
    
    html = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_chunk = " ".join(text_old.split()[i1:i2])
        new_chunk = " ".join(text_new.split()[j1:j2])
        
        if tag == 'replace':
            html.append(f'<span style="background-color: rgba(255, 99, 132, 0.4); text-decoration: line-through; padding: 2px; border-radius: 3px;">{old_chunk}</span> <span style="background-color: rgba(75, 192, 192, 0.4); padding: 2px; border-radius: 3px;">{new_chunk}</span>')
        elif tag == 'delete':
            html.append(f'<span style="background-color: rgba(255, 99, 132, 0.4); text-decoration: line-through; padding: 2px; border-radius: 3px;">{old_chunk}</span>')
        elif tag == 'insert':
            html.append(f'<span style="background-color: rgba(75, 192, 192, 0.4); padding: 2px; border-radius: 3px;">{new_chunk}</span>')
        elif tag == 'equal':
            html.append(old_chunk)
            
    return " ".join(html)


def semantic_diff_chunk(old_text: str, new_text: str) -> dict:
    """
    Сравнивает два текста по их семантическому вектору e5-small.
    Возвращает словарь с категорией и HTML-разметкой изменений.
    """
    vec_old = embed_text(old_text, is_query=False)
    vec_new = embed_text(new_text, is_query=False)
    
    v1 = vec_old.astype(np.float32)
    v2 = vec_new.astype(np.float32)
    
    score = float(np.dot(v1, v2))
    
    if score > 0.95:
        category = "unchanged"
        html_diff = new_text
    elif score > 0.70:
        category = "modified"
        html_diff = highlight_text_diff(old_text, new_text)
    else:
        category = "new_meaning"
        html_diff = f'<div style="background-color: rgba(255, 99, 132, 0.2); text-decoration: line-through; margin-bottom: 5px; padding: 5px; border-radius: 5px;">{old_text}</div><div style="background-color: rgba(75, 192, 192, 0.2); padding: 5px; border-radius: 5px;">{new_text}</div>'
        
    return {
        "score": round(score, 4),
        "category": category,
        "old_text": old_text,
        "new_text": new_text,
        "html_diff": html_diff
    }
