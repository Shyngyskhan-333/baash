
import networkx as nx
from pyvis.network import Network
from pathlib import Path

OUTPUT_DIR = Path("app")
OUTPUT_DIR.mkdir(exist_ok=True)

EDGE_COLORS = {
    "reference":     "#4a9eff",
    "duplicate":     "#ffd700",
    "contradiction": "#ff4444",
    "outdated":      "#ff8c00",
}

NODE_OK      = "#6c63ff"
NODE_WARNING = "#ff8c00"
NODE_DANGER  = "#ff4444"

def build_graph(documents: list, problems: list) -> nx.DiGraph:
    G = nx.DiGraph()

    for doc in documents:
        G.add_node(doc["id"],
                   label=doc["title"][:45] + ("…" if len(doc["title"]) > 45 else ""),
                   title=doc["title"],
                   date=doc.get("date", ""),
                   url=doc.get("url", ""),
                   problem_count=0,
                   problem_types=set())

    for doc in documents:
        for ref in doc.get("references", []):
            if G.has_node(ref) and ref != doc["id"]:
                G.add_edge(doc["id"], ref, type="reference", weight=1)

    for p in problems:
        if p.article_b is None:
            node = p.article_a["doc_id"]
            if G.has_node(node):
                G.nodes[node]["problem_count"] += 1
                G.nodes[node]["problem_types"].add(p.type)
            continue

        src = p.article_a["doc_id"]
        dst = p.article_b["doc_id"]

        if src != dst and G.has_node(src) and G.has_node(dst):
            G.add_edge(src, dst,
                       type=p.type,
                       score=round(p.score, 3),
                       title=f"{p.type} | score={p.score:.2f}")
            for node in [src, dst]:
                G.nodes[node]["problem_count"] += 1
                G.nodes[node]["problem_types"].add(p.type)

    return G

def render_graph(G: nx.DiGraph, output: str = "app/graph.html") -> str:
    net = Network(
        height="580px", width="100%",
        directed=True,
        bgcolor="#0e1117",
        font_color="#ffffff",
    )
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=200)

    for node, data in G.nodes(data=True):
        pc = data.get("problem_count", 0)
        size = 20 + min(pc * 8, 60)

        if pc == 0:
            color = NODE_OK
        elif pc <= 2:
            color = NODE_WARNING
        else:
            color = NODE_DANGER

        types_str = ", ".join(data.get("problem_types", set()))
        tooltip = (
            f"<b>{data.get('title', node)}</b><br>"
            f"Дата: {data.get('date','')}<br>"
            f"Проблем: {pc}"
            + (f"<br>Типы: {types_str}" if types_str else "")
        )
        net.add_node(node,
                     label=data.get("label", node),
                     size=size,
                     color=color,
                     title=tooltip)

    for src, dst, data in G.edges(data=True):
        etype = data.get("type", "reference")
        net.add_edge(src, dst,
                     color=EDGE_COLORS.get(etype, "#ffffff"),
                     title=data.get("title", etype),
                     width=2 if etype == "reference" else 3,
                     dashes=(etype == "reference"))

    legend = [
        ("Ссылка",       EDGE_COLORS["reference"],     "L_ref"),
        ("Дубль",        EDGE_COLORS["duplicate"],      "L_dup"),
        ("Противоречие", EDGE_COLORS["contradiction"],  "L_con"),
        ("Устаревшее",   EDGE_COLORS["outdated"],       "L_old"),
    ]
    for label, color, lid in legend:
        net.add_node(lid, label=label, color=color,
                     size=12, shape="dot", x=-600, physics=False)

    net.save_graph(output)
    return output

def graph_stats(G: nx.DiGraph) -> dict:
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "problematic_nodes": sum(
            1 for _, d in G.nodes(data=True) if d.get("problem_count", 0) > 0
        ),
        "most_connected": sorted(
            G.nodes, key=lambda n: G.degree(n), reverse=True
        )[:5],
    }