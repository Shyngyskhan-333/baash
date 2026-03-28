"""
Streamlit Dashboard — Legal Entropy KZ
Запуск: streamlit run app/dashboard.py
"""
import streamlit as st
import streamlit.components.v1 as components
import json, sys
import shutil
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.parser.adilet_scraper import parse_batch, SAMPLE_DOC_IDS, fetch_and_parse_previous_edition
from src.nlp.embedder          import prepare_articles, embed_texts, save_embeddings, load_embeddings, build_index
from src.nlp.detector          import run_all_detectors
from src.nlp.explainer         import explain, explain_version_diff
from src.nlp.version_compare   import full_version_compare, VERSION_SEMANTIC_CHANGE_MAX
from src.graph.law_graph       import build_graph, render_graph, graph_stats
import difflib

PARSED_DIR = Path("data/parsed")
RAW_DIR = Path("data/raw")
CACHE_DIR = Path("data/cache")
EMBED_CACHE_FILES = ("main_embeddings.npy", "main_articles.pkl", "main.index")

def highlight_texts(text1: str, text2: str):
    matcher = difflib.SequenceMatcher(None, text1, text2)
    res1, res2 = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            chunk = text1[i1:i2]
            if len(chunk.strip()) > 3:
                res1.append(f"<mark style='background-color: rgba(255, 215, 0, 0.4);'>{chunk}</mark>")
                res2.append(f"<mark style='background-color: rgba(255, 215, 0, 0.4);'>{chunk}</mark>")
            else:
                res1.append(chunk)
                res2.append(chunk)
        else:
            res1.append(text1[i1:i2])
            res2.append(text2[j1:j2])
    return "".join(res1), "".join(res2)

def load_cached_doc_entries():
    entries = []
    for p in sorted(PARSED_DIR.glob("*.json")):
        doc_id = p.stem
        title = doc_id
        try:
            with open(p, encoding="utf-8") as f:
                doc = json.load(f)
            title = doc.get("title", title)
        except Exception:
            pass
        size_kb = p.stat().st_size / 1024
        label = f"{title[:70]} — {doc_id} ({size_kb:.1f} KB)"
        entries.append({"id": doc_id, "path": p, "label": label})
    return entries

def load_cached_docs():
    cached = []
    for p in sorted(PARSED_DIR.glob("*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                cached.append(json.load(f))
        except Exception:
            pass
    return cached

def clear_embedding_cache() -> int:
    removed = 0
    for filename in EMBED_CACHE_FILES:
        path = CACHE_DIR / filename
        if path.exists():
            path.unlink()
            removed += 1
    chroma_dir = CACHE_DIR / "chroma"
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir, ignore_errors=True)
        removed += 1
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return removed

def delete_cached_documents(doc_ids: list[str]) -> dict:
    parsed_deleted = 0
    raw_deleted = 0
    errors = []

    for doc_id in doc_ids:
        parsed_path = PARSED_DIR / f"{doc_id}.json"
        if parsed_path.exists():
            try:
                parsed_path.unlink()
                parsed_deleted += 1
            except Exception as e:
                errors.append(f"{doc_id}: {e}")

        base_id = doc_id.split("_prev_")[0]
        patterns = [
            f"{doc_id}.html",
            f"{doc_id}_history.html",
            f"archive_{doc_id}_*.html",
        ]
        if base_id != doc_id:
            patterns.extend(
                [
                    f"{base_id}.html",
                    f"{base_id}_history.html",
                    f"archive_{base_id}_*.html",
                ]
            )
        for pattern in patterns:
            for raw_path in RAW_DIR.glob(pattern):
                if not raw_path.is_file():
                    continue
                try:
                    raw_path.unlink()
                    raw_deleted += 1
                except Exception as e:
                    errors.append(f"{raw_path.name}: {e}")

    embed_deleted = clear_embedding_cache()
    return {
        "parsed_deleted": parsed_deleted,
        "raw_deleted": raw_deleted,
        "embed_deleted": embed_deleted,
        "errors": errors,
    }

def clear_analysis_state() -> None:
    keys_to_drop = {
        "docs",
        "results",
        "articles",
        "version_prev_by_base",
        "version_compare_cache",
        "ver_base_doc_pick",
    }
    for key in list(st.session_state.keys()):
        if key in keys_to_drop or key.startswith(("dup_", "con_", "old_", "ver_ai_")):
            del st.session_state[key]

def reset_tab_once_buttons() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("tab_btn_once_"):
            del st.session_state[key]

st.set_page_config(page_title="Legal Entropy KZ", layout="wide")

st.markdown("""<style>
.stButton>button{width:100%}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("Legal Entropy KZ")
    st.caption("AI-анализ нормативных актов Казахстана")
    st.divider()
    source = st.radio("Источник", ["Демо (Әділет)", "Загрузить JSON"])
    uploaded_files = None
    if source == "Загрузить JSON":
        uploaded_files = st.file_uploader("НПА (JSON)", accept_multiple_files=True, type=["json"])
    dup_thresh = st.slider("Порог дублей", 0.80, 0.99, 0.90, 0.01)
    con_thresh = st.slider(
        "Нижняя граница сходства (кандидаты в противоречия)",
        0.60,
        0.89,
        0.85,
        0.01,
    )
    run_btn = st.button("Запустить анализ", type="primary", use_container_width=True)
    st.divider()
    st.subheader("Очистка кэша")
    cache_entries = load_cached_doc_entries()
    if cache_entries:
        selected_for_delete = st.multiselect(
            "Выберите документы",
            options=[item["id"] for item in cache_entries],
            format_func=lambda doc_id: next(
                item["label"] for item in cache_entries if item["id"] == doc_id
            ),
            key="cache_docs_to_delete",
            help="Удаляются выбранные JSON в data/parsed и связанные HTML-кэши в data/raw.",
        )
        if st.button("Удалить выбранные из кэша", type="secondary", use_container_width=True):
            if not selected_for_delete:
                st.warning("Сначала выберите минимум один документ.")
            else:
                result = delete_cached_documents(selected_for_delete)
                clear_analysis_state()
                st.success(
                    f"Удалено: parsed={result['parsed_deleted']}, raw={result['raw_deleted']}, "
                    f"embedding-cache={result['embed_deleted']}."
                )
                if result["errors"]:
                    st.warning("Некоторые файлы не удалось удалить:\n- " + "\n- ".join(result["errors"][:10]))
    else:
        st.caption("Кэш документов пуст.")

st.title("Законодательная энтропия")
st.caption("Дубли · Противоречия · Устаревшие нормы — AI-анализ НПА Казахстана")

# Auto-load any already-parsed documents on first visit
cached_docs = load_cached_docs()
if cached_docs and "results" not in st.session_state:
    st.info(f"Найдено {len(cached_docs)} документов в кэше. Нажмите **Запустить анализ** для обработки.")

if run_btn:
    reset_tab_once_buttons()
    with st.status("Анализируем...", expanded=True) as status:
        if uploaded_files:
            docs = [json.load(f) for f in uploaded_files]
        else:
            # Load from local cache first, then fetch missing ones
            st.write("Загружаем кэшированные документы...")
            docs = load_cached_docs()
            if not docs:
                st.write("Кэш пуст — парсим Әділет (может занять ~2 мин)...")
                docs = parse_batch(SAMPLE_DOC_IDS)
                docs = load_cached_docs()  # reload after parse
            else:
                st.write(f"Загружено из кэша: {len(docs)} документов")

        if not docs:
            st.error("Нет документов. Запустите парсер: python src/parser/adilet_scraper.py")
            st.stop()

        articles, texts = prepare_articles(docs)
        st.write(f"Документов: {len(docs)}, статей: {len(texts)}")

        try:
            embeddings, articles, faiss_index = load_embeddings()
            st.write("Embeddings из кэша")
        except Exception:
            st.write("Строим embeddings (BGE-M3)...")
            embeddings = embed_texts(texts)
            save_embeddings(embeddings, articles)
            
            from src.nlp.embedder import unload_model
            unload_model()
            faiss_index = build_index(embeddings)

        import src.nlp.detector as det
        det.DUPLICATE_THRESHOLD = dup_thresh
        det.CONTRADICTION_LOW   = con_thresh

        st.write("Запускаем детекторы...")
        results = run_all_detectors(embeddings, articles, faiss_index=faiss_index)
        
        from src.nlp.nli_infer import unload_nli
        unload_nli()
        
        status.update(label="Готово!", state="complete")

    st.session_state.update({"docs": docs, "results": results, "articles": articles})

if "results" in st.session_state:
    results  = st.session_state["results"]
    docs     = st.session_state["docs"]
    dups, cons, olds = results["duplicates"], results["contradictions"], results["outdated"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("НПА", len(docs))
    c2.metric("Дубли", len(dups))
    c3.metric("Противоречия", len(cons))
    c4.metric("Устаревших", len(olds))
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Граф", "Дубли", "Противоречия", "Устаревшие", "Изменения версий"]
    )

    with tab1:
        G = build_graph(docs, results["all"])
        s = graph_stats(G)
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Законов", s["nodes"])
        cc2.metric("Связей", s["edges"])
        cc3.metric("Проблемных", s["problematic_nodes"])
        path = render_graph(G, "app/graph.html")
        with open(path, encoding="utf-8") as f:
            components.html(f.read(), height=600)
        st.caption("🟡 Дубль | 🔴 Противоречие | 🟠 Устаревшее | 🔵 Ссылка")

    def show_problems(problems, prefix, icon):
        if not problems:
            st.info("Проблем не найдено.")
            return
        for i, p in enumerate(problems[:30]):
            ta = p.article_a.get("doc_title", p.article_a["doc_id"])
            tb = p.article_b.get("doc_title", p.article_b["doc_id"]) if p.article_b else ""
            label = f"{icon} score={p.score:.2f} | {ta[:80]}..." + (f" ↔ {tb[:80]}..." if tb else "")
            with st.expander(label):
                if p.article_b:
                    ca, cb = st.columns(2)
                    t1, t2 = highlight_texts(p.article_a["text"], p.article_b["text"])
                    with ca:
                        st.markdown(f"**{ta}**")
                        st.markdown(f"<div style='height:250px; overflow-y:auto; border:1px solid #ccc; padding:10px; border-radius:5px;'>{t1}</div>", unsafe_allow_html=True)
                    with cb:
                        st.markdown(f"**{tb}**")
                        st.markdown(f"<div style='height:250px; overflow-y:auto; border:1px solid #ccc; padding:10px; border-radius:5px;'>{t2}</div>", unsafe_allow_html=True)
                        
                    st.write("---")
                    st.markdown("##### 🌳 AI-Вердикт (Decision Tree)")
                    st.caption("Схожесть темы (семантический вектор)")
                    st.progress(p.score, text=f"{p.score*100:.1f}%")
                    
                    if p.type == 'contradiction':
                        st.caption("Вероятность противоречия (NLI-модель)")
                        st.progress(p.nli_score, text=f"{p.nli_score*100:.1f}%")
                else:
                    st.text_area("", p.article_a["text"], height=200, key=f"{prefix}_a_{i}", disabled=True)
                    if p.type == "outdated":
                        st.caption("Семантическая близость к шаблону утраты силы (косинус с якорем)")
                        st.progress(min(max(p.score, 0.0), 1.0), text=f"{p.score*100:.1f}%")
                    if p.explanation:
                        st.warning(p.explanation)
                exp_key = f"{prefix}_exp_result_{i}"
                btn_once_key = f"tab_btn_once_{prefix}_exp_{i}"
                btn_slot = st.empty()
                if exp_key not in st.session_state and not st.session_state.get(btn_once_key, False):
                    if btn_slot.button("💡 Объяснить (AI)", key=f"{prefix}_exp_btn_{i}"):
                        st.session_state[btn_once_key] = True
                        btn_slot.empty()
                        st.session_state[exp_key] = explain(p)
                
                if exp_key in st.session_state:
                    st.info(st.session_state[exp_key])

    with tab2:
        st.subheader(f"Дублирующиеся нормы — {len(dups)}")
        show_problems(dups, "dup", "🔁")
    with tab3:
        st.subheader(f"Противоречия — {len(cons)}")
        show_problems(cons, "con", "⚡")
    with tab4:
        st.subheader(f"Устаревшие нормы — {len(olds)}")
        show_problems(olds, "old", "🕰️")

    def _load_prev_from_disk(base_id: str):
        paths = list(PARSED_DIR.glob(f"{base_id}_prev_*.json"))
        if not paths:
            return None
        latest = max(paths, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    with tab5:
        st.subheader("Сравнение с предыдущей редакцией (Әділет)")
        st.caption(
            "Загрузите предыдущую редакцию из истории изменений на adilet.zan.kz; "
            "статьи сопоставляются по номеру «Статья N», близость — косинус эмбеддингов."
        )
        base_candidates = [
            d for d in docs if not d.get("is_archive_edition") and "_prev_" not in str(d.get("id", ""))
        ]
        if not base_candidates:
            base_candidates = docs
        labels = [f"{d.get('title', d.get('id', '?'))[:70]} — {d.get('id', '')}" for d in base_candidates]
        pick = st.selectbox(
            "Базовый НПА (текущая редакция)",
            list(range(len(base_candidates))),
            format_func=lambda i: labels[i],
            key="ver_base_doc_pick",
        )
        cur_doc = base_candidates[pick]
        base_id = cur_doc.get("id") or ""

        if "version_prev_by_base" not in st.session_state:
            st.session_state["version_prev_by_base"] = {}

        prev_doc = st.session_state["version_prev_by_base"].get(base_id) or _load_prev_from_disk(base_id)
        fetch_prev_once_key = "tab_btn_once_fetch_prev_edition"

        c_prev1, c_prev2 = st.columns([1, 2])
        with c_prev1:
            fetch_btn_slot = st.empty()
            if not st.session_state.get(fetch_prev_once_key, False):
                if fetch_btn_slot.button(
                    "Загрузить предыдущую редакцию", key="fetch_prev_edition", use_container_width=True
                ):
                    st.session_state[fetch_prev_once_key] = True
                    fetch_btn_slot.empty()
                    loaded = fetch_and_parse_previous_edition(base_id)
                    if loaded:
                        st.session_state["version_prev_by_base"][base_id] = loaded
                        prev_doc = loaded
                        st.success(f"Загружена редакция от {loaded.get('edition_date', '?')}")
                    else:
                        st.warning("Нет предпоследней редакции в истории или ошибка загрузки.")
        with c_prev2:
            if prev_doc:
                st.info(
                    f"Предыдущая редакция: **{prev_doc.get('edition_date', '?')}** "
                    f"(`{prev_doc.get('id', '')}`)"
                )
            else:
                st.info("Предыдущая редакция не загружена. Нажмите кнопку слева (нужен доступ к adilet.zan.kz).")

        if prev_doc:
            if "version_compare_cache" not in st.session_state:
                st.session_state["version_compare_cache"] = {}
            compare_key = (
                f"{cur_doc.get('id', '')}|{prev_doc.get('id', '')}|"
                f"{cur_doc.get('date', '')}|{prev_doc.get('edition_date', '')}"
            )
            report = st.session_state["version_compare_cache"].get(compare_key)
            if report is None:
                report = full_version_compare(prev_doc, cur_doc, merge_chunks=True)
                st.session_state["version_compare_cache"][compare_key] = report

            st.metric("Сопоставленных статей (по номеру)", report["paired_count"])
            if report["only_old"]:
                with st.expander(f"Только в предыдущей редакции — {len(report['only_old'])}"):
                    for a in report["only_old"][:40]:
                        st.text((a.get("number") or a.get("id", ""))[:120])
            if report["only_new"]:
                with st.expander(f"Только в текущей редакции — {len(report['only_new'])}"):
                    for a in report["only_new"][:40]:
                        st.text((a.get("number") or a.get("id", ""))[:120])

            for vidx, row in enumerate(report["pairs_detail"]):
                num = row["article_num"]
                sc = row["score"]
                lbl = row["label"]
                if lbl == "unchanged":
                    badge = "🟢 без существенных изменений"
                elif lbl == "minor":
                    badge = "🟡 возможны правки"
                else:
                    badge = "🔴 смысловое изменение"
                exp_label = f"Статья {num} · cos={sc:.4f} · {badge}"
                with st.expander(exp_label):
                    ao, an = row["article_old"], row["article_new"]
                    ca, cb = st.columns(2)
                    t1, t2 = highlight_texts(ao.get("text", ""), an.get("text", ""))
                    title_old = f"{prev_doc.get('title', '')} ({prev_doc.get('edition_date', 'архив')})"
                    title_new = cur_doc.get("title", cur_doc.get("id", ""))
                    with ca:
                        st.markdown(f"**Предыдущая** — {title_old}")
                        st.markdown(
                            f"<div style='height:220px; overflow-y:auto; border:1px solid #ccc; padding:10px; border-radius:5px;'>{t1}</div>",
                            unsafe_allow_html=True,
                        )
                    with cb:
                        st.markdown(f"**Текущая** — {title_new}")
                        st.markdown(
                            f"<div style='height:220px; overflow-y:auto; border:1px solid #ccc; padding:10px; border-radius:5px;'>{t2}</div>",
                            unsafe_allow_html=True,
                        )
                    exp_key = f"ver_ai_{base_id}_{vidx}_{num}"
                    ver_btn_once_key = f"tab_btn_once_ver_ai_{base_id}_{vidx}_{num}"
                    ver_btn_slot = st.empty()
                    if sc < VERSION_SEMANTIC_CHANGE_MAX:
                        if exp_key not in st.session_state and not st.session_state.get(ver_btn_once_key, False):
                            if ver_btn_slot.button(
                                "Объяснить изменение (AI)",
                                key=f"ver_btn_{base_id}_{vidx}_{num}",
                            ):
                                st.session_state[ver_btn_once_key] = True
                                ver_btn_slot.empty()
                                st.session_state[exp_key] = explain_version_diff(
                                    ao.get("text", ""),
                                    an.get("text", ""),
                                    title_old,
                                    title_new,
                                    sc,
                                )
                        if exp_key in st.session_state:
                            st.info(st.session_state[exp_key])
                    else:
                        st.caption("Кнопка AI доступна при косинусе ниже 0.95 (смысловое изменение).")
