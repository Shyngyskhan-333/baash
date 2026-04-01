"""
Knowledge Graph Builder.
Строит граф связей между НПА и конкретными статьями.
Ререндерит интерактивный HTML (PyVis) и Plotly Heatmap.
"""
import pickle
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.express as px
from pyvis.network import Network

class LegalKnowledgeGraph:
    def __init__(self, data_dir: str = "data"):
        self.graph_path = Path(data_dir) / "faiss" / "graph.pkl"
        self.G = nx.DiGraph()
        self.load()
        
    def load(self):
        if self.graph_path.exists():
            with open(self.graph_path, "rb") as f:
                self.G = pickle.load(f)
                
    def save(self):
        with open(self.graph_path, "wb") as f:
            pickle.dump(self.G, f)
            
    def add_node(self, node_id: str, **metadata):
        self.G.add_node(node_id, **metadata)
        
    def add_edge(self, source: str, target: str, rel_type: str, weight: float = 1.0):
        """ rel_type: 'reference', 'contradiction', 'duplicate', 'outdated' """
        self.G.add_edge(source, target, type=rel_type, weight=weight)
        
    def build_from_detector_problems(self, problems: list):
        """Парсит список проблем (Problem dataclass) и строит по ним граф"""
        self.G.clear()
        
        for p in problems:
            id_a = p.chunk_a['chunk_id']
            id_b = p.chunk_b['chunk_id']
            
            if not self.G.has_node(id_a):
                self.add_node(id_a, label=f"{p.chunk_a['doc_title'][:30]}\n({p.chunk_a['article_number']})", doc_id=p.chunk_a['doc_title'])
            if not self.G.has_node(id_b):
                self.add_node(id_b, label=f"{p.chunk_b['doc_title'][:30]}\n({p.chunk_b['article_number']})", doc_id=p.chunk_b['doc_title'])
                
            self.add_edge(id_a, id_b, rel_type=p.type, weight=1.0)
            
        self.save()

    def generate_pyvis_html(self, filter_type=None) -> str:
        """Создает интерактивный граф PyVis (html строка) для встраивания в Streamlit"""
        colors = {
            "contradiction": "#ff4b4b", # красный
            "outdated": "#ffeb3b",      # желтый
            "duplicate": "#4b7bff",     # синий
            "reference": "#4caf50"      # зеленый
        }
        
        net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black", directed=True, cdn_resources='remote')
        net.barnes_hut() # Гравитационная физика графа
        
        for node_id, data in self.G.nodes(data=True):
            net.add_node(node_id, label=data.get("label", node_id), title=data.get("doc_id", node_id))
            
        for u, v, data in self.G.edges(data=True):
            r_type = data.get("type", "reference")
            
            if filter_type and filter_type != "All":
                if filter_type == "Противоречия" and r_type != "contradiction":
                    continue
                if filter_type == "Дубли" and r_type != "duplicate":
                    continue
                if filter_type == "Устаревшие" and r_type != "outdated":
                    continue
                
            color = colors.get(r_type, "#cccccc")
            net.add_edge(u, v, title=r_type, color=color, value=data.get("weight", 1.0))
            
        tmp_path = Path("data/faiss/tmp_graph.html")
        net.save_graph(str(tmp_path))
        html_data = tmp_path.read_text(encoding="utf-8")
        return html_data

    def generate_heatmap_fig(self):
        """Создает Plotly Heatmap по количеству проблем на каждый закон (Heatmap)"""
        law_problems = {} # {doc_title: {"contradiction": X, "duplicate": Y, "outdated": Z}}
        
        for u, v, data in self.G.edges(data=True):
            u_doc = self.G.nodes[u].get("doc_id", u)
            v_doc = self.G.nodes[v].get("doc_id", v)
            rel_type = data.get("type", "unknown")
            
            for doc in [u_doc, v_doc]:
                if doc not in law_problems:
                    law_problems[doc] = {"contradiction": 0, "duplicate": 0, "outdated": 0}
                if rel_type in law_problems[doc]:
                    law_problems[doc][rel_type] += 1
                    
        if not law_problems:
            return None
            
        df = pd.DataFrame.from_dict(law_problems, orient="index")
        
        fig = px.imshow(
            df, 
            text_auto=True, 
            color_continuous_scale="Reds",
            labels=dict(x="Тип проблемы", y="Законопроект", color="Количество коллизий"),
            title="🌡 Тепловая карта проблемности законодательства"
        )
        return fig
