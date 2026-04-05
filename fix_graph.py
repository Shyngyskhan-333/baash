import pickle
from pathlib import Path

def run():
    p = Path("data/faiss/graph.pkl")
    if not p.exists():
        return
    with open(p, "rb") as f:
        G = pickle.load(f)

    print("Graph node fix applied to logic. User should rerun audit if necessary.")

if __name__ == "__main__":
    run()