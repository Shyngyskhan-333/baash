
import pickle
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.express as px
from pyvis.network import Network

class LegalKnowledgeGraph:
    def __init__(self, data_dir: str = "data"):
        self.graph_path = Path(data_dir) / "faiss" / "graph.pkl"

        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.G = nx.DiGraph()
        self.load()

    def load(self):
        if self.graph_path.exists():
            try:
                with open(self.graph_path, "rb") as f:
                    self.G = pickle.load(f)
            except Exception as e:
                print(f"[GRAPH_LOAD_ERROR] {e}. Starting with empty graph.")
                self.G = nx.DiGraph()

    def save(self):
        try:
            with open(self.graph_path, "wb") as f:
                pickle.dump(self.G, f)
        except Exception as e:
            print(f"[GRAPH_SAVE_ERROR] {e}")

    def add_node(self, node_id: str, **metadata):
        self.G.add_node(node_id, **metadata)

    def add_edge(self, source: str, target: str, rel_type: str, weight: float = 1.0):

        self.G.add_edge(source, target, type=rel_type, weight=weight)

    def ensure_doc_node(self, doc_id: str, title: str):

        if not self.G.has_node(doc_id):
            self.add_node(
                doc_id,
                label=title[:40],
                doc_id=doc_id,
                doc_title=title,
                is_document=True,
            )
            self.save()

    def append_problems(self, problems: list, clear: bool = False):

        if clear:
            self.G.clear()

        for p in problems:

            try:
                chunk_a = p.chunk_a if hasattr(p, "chunk_a") else p["chunk_a"]
                chunk_b = p.chunk_b if hasattr(p, "chunk_b") else p["chunk_b"]
                p_type = p.type if hasattr(p, "type") else p["type"]
            except (KeyError, AttributeError):
                continue

            id_a = chunk_a["chunk_id"]
            id_b = chunk_b["chunk_id"]

            if not self.G.has_node(id_a):
                self.add_node(
                    id_a,
                    label=f"{chunk_a['doc_title'][:30]}\n({chunk_a['article_number']})",
                    doc_id=chunk_a.get("doc_id", chunk_a["doc_title"]),
                    doc_title=chunk_a["doc_title"],
                )
            if not self.G.has_node(id_b):
                self.add_node(
                    id_b,
                    label=f"{chunk_b['doc_title'][:30]}\n({chunk_b['article_number']})",
                    doc_id=chunk_b.get("doc_id", chunk_b["doc_title"]),
                    doc_title=chunk_b["doc_title"],
                )

            self.add_edge(id_a, id_b, rel_type=p_type, weight=1.0)

        self.save()

    def build_from_detector_problems(self, problems: list):

        self.append_problems(problems, clear=True)

    def generate_pyvis_html(self, filter_type=None, doc_ids: list = None) -> str:

        colors = {
            "contradiction": "#ff4b4b",
            "outdated": "#ffeb3b",
            "duplicate": "#4b7bff",
            "reference": "#4caf50",
            "neutral": "#9e9e9e",
            "entailment": "#8bc34a",
        }

        net = Network(
            height="600px",
            width="100%",
            bgcolor="#ffffff",
            font_color="black",
            directed=True,
            cdn_resources="remote",
        )

        net.set_options(
            
        )

        try:
            pr = nx.pagerank(self.G)
            min_pr = min(pr.values()) if pr else 0
            max_pr = max(pr.values()) if pr else 1
        except Exception:
            pr = {}
            min_pr, max_pr = 0, 1

        def get_node_size(n_id):
            if not pr or max_pr == min_pr:
                return 30
            norm = (pr.get(n_id, 0) - min_pr) / (max_pr - min_pr)
            return 25 + (norm * 45)

        edges_to_draw = []
        nodes_with_edges = set()

        for u, v, data in self.G.edges(data=True):
            r_type = data.get("type", "reference")

            if not doc_ids and r_type in ["reference", "neutral", "entailment"]:
                continue

            if filter_type and filter_type not in ["All", "Все"]:
                if filter_type == "Противоречия" and r_type != "contradiction":
                    continue
                if filter_type == "Дубли" and r_type != "duplicate":
                    continue
                if filter_type == "Устаревшие" and r_type != "outdated":
                    continue

            edges_to_draw.append((u, v, r_type, data.get("weight", 1.0)))
            nodes_with_edges.add(u)
            nodes_with_edges.add(v)

        for node_id, data in self.G.nodes(data=True):
            node_doc = data.get("doc_id")

            if doc_ids:

                if node_doc not in doc_ids:
                    continue
            else:

                if node_id not in nodes_with_edges:
                    continue

            net.add_node(
                node_id,
                label=data.get("label", node_id),
                title=f"{data.get('doc_title', node_doc)}\nКликните для анализа",
                doc_id=node_doc,
                size=get_node_size(node_id),
                font={"size": 14},
            )

        added_node_ids = {n["id"] for n in net.nodes}
        for u, v, r_type, weight in edges_to_draw:
            if u in added_node_ids and v in added_node_ids:
                color = colors.get(r_type, "#cccccc")
                net.add_edge(u, v, title=r_type, color=color, value=weight)

        tmp_path = Path("data/faiss/tmp_graph.html")
        net.save_graph(str(tmp_path))
        html_data = tmp_path.read_text(encoding="utf-8")

        click_js = 
        html_data = html_data.replace("</body>", click_js + "</body>")

        return html_data

    def generate_heatmap_fig(self, doc_ids: list = None):

        law_problems = {}

        for u, v, data in self.G.edges(data=True):
            u_doc_id = self.G.nodes[u].get("doc_id", u)
            v_doc_id = self.G.nodes[v].get("doc_id", v)
            u_doc_title = self.G.nodes[u].get("doc_title", u_doc_id)
            v_doc_title = self.G.nodes[v].get("doc_title", v_doc_id)
            rel_type = data.get("type", "unknown")

            for doc_id_val, doc_title_val in [(u_doc_id, u_doc_title), (v_doc_id, v_doc_title)]:

                if doc_ids and doc_id_val not in doc_ids:
                    continue

                if doc_title_val not in law_problems:
                    law_problems[doc_title_val] = {
                        "contradiction": 0,
                        "duplicate": 0,
                        "outdated": 0,
                    }
                if rel_type in law_problems[doc_title_val]:
                    law_problems[doc_title_val][rel_type] += 1

        if not law_problems:
            return None

        df = pd.DataFrame.from_dict(law_problems, orient="index")

        fig = px.imshow(
            df,
            text_auto=True,
            color_continuous_scale="Reds",
            labels=dict(
                x="Тип проблемы",
                y="Законопроект",
                color="Количество коллизий",
            ),
            title="Тепловая карта проблемности законодательства",
        )
        return fig