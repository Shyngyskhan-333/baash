import streamlit as st
import sys
import os
import streamlit.components.v1 as components
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.scraper.adilet_scraper import parse_batch
from src.retrieval.retriever import LegalRetriever
from src.reasoning.detector import detect_all_problems
from src.reasoning.version_compare import semantic_diff_chunk
from src.graph.knowledge_graph import LegalKnowledgeGraph

st.set_page_config(page_title="LexEntropy KZ", layout="wide")

st.title("LexEntropy KZ - Анализ законодательства")
st.markdown("**(Оптимизировано для CPU)** Гибридный поиск: FAISS + BM25, Анализ NLI: DeBERTa, Чанкинг: Юридический.")

@st.cache_resource
def get_retriever():
    return LegalRetriever()

@st.cache_resource
def get_graph():
    return LegalKnowledgeGraph()

retriever = get_retriever()
graph = get_graph()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Индексация", 
    "2. Гибридный Поиск", 
    "3. Аудит Коллизий", 
    "4. Версионирование", 
    "5. Граф Знаний & Heatmap"
])

with tab1:
    st.header("Загрузка и Парсинг НПА (Adilet)")
    st.info("Данные скачиваются, разбиваются на иерархию и превращаются в легковесные эмбеддинги e5-small.")
    
    doc_ids_input = st.text_input("Введите ID документа (например K1500000377, K1400000266 через запятую):")
    
    col_run1, col_run2 = st.columns([1, 4])
    with col_run1:
        btn_index = st.button("--build-index", type="primary", use_container_width=True)
    
    if btn_index:
        with st.spinner("Загрузка, парсинг и векторизация e5-small..."):
            ids = [x.strip() for x in doc_ids_input.split(",") if x.strip()]
            if ids:
                docs = parse_batch(ids)
                if docs:
                    added = retriever.add_documents(docs)
                    st.success(f"Успешно обработано: {added} чанков (статей/пунктов).")
                    st.cache_resource.clear()
                else:
                    st.warning("Не удалось скачать документы или они уже проиндексированы.")
            else:
                st.error("Введите ID документа.")
        
with tab2:
    st.header("Гибридный поиск (BM25 + Semantic FAISS)")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Запрос (например: 'требования к учредителям ТОО'):")
    with col2:
        top_k = st.number_input("Сколько результатов?", min_value=1, max_value=20, value=5)
        
    col_run1, _ = st.columns([1, 4])
    with col_run1:
        btn_query = st.button('--query "текст"', type="primary", use_container_width=True)
        
    if btn_query and query:
        with st.spinner("Моментальный поиск... (RRF)"):
            results = retriever.search_hybrid(query, top_k=top_k)
            if not results:
                st.write("Ничего не найдено.")
            for i, res in enumerate(results, 1):
                with st.expander(f"#{i} — {res['doc_title']} (Статья {res['article_number']}) — RRF: {res['rrf_score']:.3f}"):
                    metrics_col1, metrics_col2 = st.columns(2)
                    metrics_col1.metric("FAISS Cosine", f"{res['cosine_score']:.3f}")
                    metrics_col2.metric("BM25 Text Search", f"{res['bm25_score']:.1f}")
                    st.write(res['text'])

with tab3:
    st.header("Поиск Противоречий и Коллизий")
    st.markdown("**Сверхбыстрый пайплайн:** `Top-10 (FAISS) -> Cosine > 0.90 -> Top-5 (NLI) -> LLM JSON`")
    
    col_run1, _ = st.columns([1, 4])
    with col_run1:
        btn_detect = st.button("--detect-contradictions", type="primary", use_container_width=True)
    
    if btn_detect:
        with st.spinner("Анализ O(N)... Ищем коллизии в базе (это займет время в зависимости от объема)"):
            problems = detect_all_problems(retriever)
            
            graph.build_from_detector_problems(problems)
            
            p_cont = [p for p in problems if p.type == "contradiction"]
            p_dup = [p for p in problems if p.type == "duplicate"]
            p_out = [p for p in problems if p.type == "outdated"]
            
            st.subheader(f"Противоречия (Коллизии): {len(p_cont)}")
            for p in p_cont:
                with st.expander(f"Противоречие: {p.chunk_a['article_number']} vs {p.chunk_b['article_number']}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**{p.chunk_a['doc_title']}**")
                        st.info(p.chunk_a['text'])
                    with col_b:
                        st.markdown(f"**{p.chunk_b['doc_title']}**")
                        st.error(p.chunk_b['text'])
                    
                    st.write(f"**Модель DeBERTa NLI (Доверие):** ~{p.scores['nli_confidence']*100:.0f}%")
                    if p.explanation:
                        st.markdown("### Результат анализа (JSON)")
                        st.json(p.explanation)
            
            st.divider()
            
            st.subheader(f"Дубликаты (Смежные по смыслу): {len(p_dup)}")
            for p in p_dup:
                with st.expander(f"Дубликат: {p.chunk_a['article_number']} vs {p.chunk_b['article_number']} (Сходство {p.scores['cosine']*100:.1f}%)"):
                    st.caption("Текст 1: " + p.chunk_a['text'])
                    st.caption("Текст 2: " + p.chunk_b['text'])

            st.divider()

            st.subheader(f"Устаревшие нормы (Утратили силу): {len(p_out)}")
            for p in p_out:
                with st.expander(f"Устарело: {p.chunk_a['doc_title']} (Статья {p.chunk_a['article_number']})"):
                    st.caption(f"Сходство с якорем: {p.scores['cosine']*100:.1f}%")
                    st.warning(p.chunk_a['text'])

with tab4:
    st.header("Семантическое Версионирование (Diff Analysis)")
    st.markdown("Сравнивает две редакции статьи нейросетью. Автоматически размечает **удаленное (красным)** и **добавленное (зеленым)**.")
    
    t_old = st.text_area("Старая редакция статьи:", height=150, value="Владелец транспортного средства обязан уплатить налог до 1 октября текущего года.")
    t_new = st.text_area("Новая редакция статьи:", height=150, value="Владелец транспортного средства должен оплачивать налог до 1 ноября отчетного года, иначе штраф.")
    
    if st.button("Сравнить семантику"):
        if t_old and t_new:
            result = semantic_diff_chunk(t_old, t_new)
            
            st.subheader("Результат:")
            col1, col2 = st.columns(2)
            col1.metric("Семантическая Близость (Cosine)", f"{result['score']*100:.1f}%")
            
            cat_color = "normal"
            if result['category'] == "unchanged":
                cat_color = "green"
            elif result['category'] == "modified":
                cat_color = "orange"
            elif result['category'] == "new_meaning":
                cat_color = "red"
                
            col2.markdown(f"**Класс изменения:** :{cat_color}[{result['category'].upper()}]")
            
            st.markdown("#### Изменения в тексте (Highlight Diff):")
            st.markdown(f"<div style='border: 1px solid #ddd; padding: 15px; border-radius: 5px; font-size: 16px;'>{result['html_diff']}</div>", unsafe_allow_html=True)
        else:
            st.warning("Введите оба текста")

with tab5:
    st.header("Graph Analyzer & Heatmap")
    st.markdown("Визуализация коллизий и проблематичных участков связей Законодательства.")
    
    if len(graph.G.nodes) == 0:
        st.info("Граф пуст. Сначала выполните 'Аудит Коллизий' (Вкладка 3), чтобы связи сформировались в базе.")
    else:
        viz_tab1, viz_tab2 = st.tabs(["Взаимосвязи (Nodes Graph)", "Heatmap Законов"])
        
        with viz_tab1:
            filt = st.selectbox("Фильтр связей:", ["Все", "Противоречия", "Дубли", "Устаревшие"])
            
            graph_html = graph.generate_pyvis_html(filter_type=filt)
            st.components.v1.html(graph_html, height=650, scrolling=True)
            
            st.markdown("""
            **Легенда:**  
            `contradiction` (Противоречие) | `duplicate` (Дубль/Повтор) | `outdated` (Устаревшая норма)
            """)
            
        with viz_tab2:
            st.markdown("Тепловая карта показывает распределение найденных коллизий по документам.")
            fig = graph.generate_heatmap_fig()
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("Недостаточно данных для построения Heatmap.")
