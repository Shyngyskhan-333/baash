from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
import hashlib
from pathlib import Path
import os

from src.graph.knowledge_graph import LegalKnowledgeGraph

router = APIRouter()
CACHE_DIR = Path("data/cache/graph")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_PATH = Path("data/faiss/graph.pkl")
DEMO_HEATMAP_PATH = CACHE_DIR / "demo_heatmap.json"
DEMO_GRAPH_PATH = CACHE_DIR / "demo_graph.html"
GRAPH_HTML_VERSION = "3"
HIDE_LOADING_STYLE = "<style>#loadingBar{display:none!important;}</style>"


def _quick_test_enabled(query_flag: Optional[bool]) -> bool:
    
    env = (os.getenv("QUICK_TEST_MODE") or os.getenv("DEMO_MODE") or "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    return bool(query_flag)


def _fast_graph_enabled() -> bool:
    env = os.getenv("GRAPH_FAST_MODE", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _latest_cached_html() -> Optional[str]:
    html_files = sorted(CACHE_DIR.glob("html_*.html"), key=lambda path: path.stat().st_mtime, reverse=True)
    if html_files:
        return html_files[0].read_text(encoding="utf-8")
    if DEMO_GRAPH_PATH.exists():
        return DEMO_GRAPH_PATH.read_text(encoding="utf-8")
    return None


def _latest_real_cached_html() -> Optional[str]:
    html_files = sorted(CACHE_DIR.glob("html_*.html"), key=lambda path: path.stat().st_mtime, reverse=True)
    if html_files:
        return html_files[0].read_text(encoding="utf-8")
    return None


def _largest_usable_cached_html() -> Optional[str]:
    
    candidates = list(CACHE_DIR.glob("html_*.html"))
    if DEMO_GRAPH_PATH.exists():
        candidates.append(DEMO_GRAPH_PATH)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    for path in candidates:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _is_usable_graph_html(content):
            return content
    return None


def _is_usable_graph_html(html: Optional[str]) -> bool:
    if not html:
        return False
    normalized = html.lower()
    return "<html" in normalized and (
        "vis-network" in normalized
        or "new vis.network" in normalized
        or 'id="mynetwork"' in normalized
    )


def _graph_exists() -> bool:
    return GRAPH_PATH.exists() and GRAPH_PATH.stat().st_size > 0


def _hide_loading_bar(html: str) -> str:
    if not html:
        return html
    if "loadingBar" in html and HIDE_LOADING_STYLE not in html:
        if "</head>" in html:
            return html.replace("</head>", f"{HIDE_LOADING_STYLE}</head>")
        return f"{HIDE_LOADING_STYLE}{html}"
    return html


def _demo_heatmap_payload() -> Optional[dict]:
    if DEMO_HEATMAP_PATH.exists():
        import json

        try:
            return json.loads(DEMO_HEATMAP_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[GRAPH] Failed to read quick-test heatmap: {exc}")
    return None


def _graph_mtime_key() -> str:
    if GRAPH_PATH.exists():
        return str(int(GRAPH_PATH.stat().st_mtime))
    return "0"


def _scope_key(doc_ids: Optional[str]) -> str:
    if not doc_ids:
        return "all"
    normalized = ",".join(sorted(set(doc_ids.split(","))))
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"scope_{digest}"


def _cache_key(suffix: str, filter_type: Optional[str], doc_ids: Optional[str]) -> Path:
    filter_key = filter_type or "all"
    raw = f"{_graph_mtime_key()}|{filter_key}|{_scope_key(doc_ids)}|{GRAPH_HTML_VERSION}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return CACHE_DIR / f"{suffix}_{digest}"


def _default_graph_filter(filter_type: Optional[str]) -> bool:
    return filter_type in {None, "", "Все", "Р’СЃРµ"}


@router.get("/graph/html", response_class=HTMLResponse)
async def get_graph_html(
    filter_type: Optional[str] = "Все",
    doc_ids: Optional[str] = None,
    quicktest: Optional[bool] = None,
    demo: Optional[bool] = None,
):
    qflag = bool(quicktest) or bool(demo)
    print(f"[GRAPH] HTML graph. Filter: {filter_type}, Scope: {doc_ids}, quicktest: {qflag}")
    is_quick_test = _quick_test_enabled(qflag)
    latest_real = _latest_real_cached_html()
    cached_preferred = (
        (_largest_usable_cached_html() or latest_real) if is_quick_test else latest_real
    )

    try:
        if not doc_ids and _default_graph_filter(filter_type) and _is_usable_graph_html(cached_preferred):
            return HTMLResponse(content=_hide_loading_bar(cached_preferred))

        if _fast_graph_enabled() or is_quick_test:
            if _graph_exists() and _is_usable_graph_html(cached_preferred):
                return HTMLResponse(content=_hide_loading_bar(cached_preferred))
            if is_quick_test and _is_usable_graph_html(cached_preferred):
                return HTMLResponse(content=_hide_loading_bar(cached_preferred))
            if DEMO_GRAPH_PATH.exists():
                return HTMLResponse(content=_hide_loading_bar(DEMO_GRAPH_PATH.read_text(encoding="utf-8")))
            cached_html = _latest_cached_html()
            if cached_html:
                return HTMLResponse(content=_hide_loading_bar(cached_html))

        graph = LegalKnowledgeGraph()
        if len(graph.G.nodes) == 0:
            if _is_usable_graph_html(cached_preferred):
                return HTMLResponse(content=_hide_loading_bar(cached_preferred))
            return HTMLResponse(
                content=
            )

        cache_path = _cache_key("html", filter_type, doc_ids).with_suffix(".html")
        if cache_path.exists():
            cached_scoped_html = cache_path.read_text(encoding="utf-8")
            if _is_usable_graph_html(cached_scoped_html):
                return HTMLResponse(content=_hide_loading_bar(cached_scoped_html))

        doc_list = doc_ids.split(",") if doc_ids else None
        html_content = graph.generate_pyvis_html(filter_type=filter_type, doc_ids=doc_list)
        if not _is_usable_graph_html(html_content) and _is_usable_graph_html(cached_preferred):
            return HTMLResponse(content=_hide_loading_bar(cached_preferred))

        html_content = _hide_loading_bar(html_content)
        cache_path.write_text(html_content, encoding="utf-8")
        return HTMLResponse(content=html_content)
    except Exception as exc:
        if _is_usable_graph_html(cached_preferred):
            return HTMLResponse(content=_hide_loading_bar(cached_preferred))
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/graph/heatmap")
async def get_graph_heatmap(
    doc_ids: Optional[str] = None,
    quicktest: Optional[bool] = None,
    demo: Optional[bool] = None,
):
    qflag = bool(quicktest) or bool(demo)
    print(f"[GRAPH] Heatmap. Scope: {doc_ids}, quicktest: {qflag}")
    try:
        if _quick_test_enabled(qflag) or _fast_graph_enabled():
            payload = _demo_heatmap_payload()
            if payload is not None:
                return JSONResponse(content=payload)

        graph = LegalKnowledgeGraph()
        if len(graph.G.nodes) == 0:
            return JSONResponse(content={"data": [], "layout": {"title": "Нет данных — запустите Аудит"}})

        cache_path = _cache_key("heatmap", "all", doc_ids).with_suffix(".json")
        if cache_path.exists():
            import json

            return JSONResponse(content=json.loads(cache_path.read_text(encoding="utf-8")))

        doc_list = doc_ids.split(",") if doc_ids else None
        fig = graph.generate_heatmap_fig(doc_ids=doc_list)
        if not fig:
            return JSONResponse(content={"data": [], "layout": {}})

        import json

        payload = json.loads(fig.to_json())
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return JSONResponse(content=payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))