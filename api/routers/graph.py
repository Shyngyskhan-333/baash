from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional

from src.graph.knowledge_graph import LegalKnowledgeGraph

router = APIRouter()

@router.get("/api/v1/graph/html", response_class=HTMLResponse)
async def get_graph_html(filter_type: Optional[str] = "Все"):
    try:
        graph = LegalKnowledgeGraph()
        if len(graph.G.nodes) == 0:
            return HTMLResponse(content="""
<html><body style="background:#1a1d27;color:#64748b;display:flex;align-items:center;justify-content:center;height:100vh;font-family:Inter,sans-serif;flex-direction:column;gap:16px">
  <svg viewBox="0 0 24 24" width="64" height="64" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
  <p style="font-size:16px">Граф пуст — запустите <b>Аудит Коллизий</b> для построения графа</p>
</body></html>
""")
        html_content = graph.generate_pyvis_html(filter_type=filter_type)
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/graph/heatmap")
async def get_graph_heatmap():
    try:
        graph = LegalKnowledgeGraph()
        if len(graph.G.nodes) == 0:
            return JSONResponse(content={"data": [], "layout": {"title": "Нет данных — запустите Аудит"}})
        fig = graph.generate_heatmap_fig()
        if not fig:
            return JSONResponse(content={"data": [], "layout": {}})
        return JSONResponse(content=fig.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
