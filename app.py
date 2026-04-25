"""
Advanced RAG Web App — EarningsIQ
===================================
Three pages:
  1. Compare — Basic RAG vs Advanced RAG side by side
  2. Advanced Chat — full chat with rewriting + re-ranking
  3. Dashboard — live system stats
"""

import streamlit as st
import chromadb
import subprocess
import time
import sys
import os

st.set_page_config(
    page_title="EarningsIQ Advanced RAG",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0a0c10; color: #e8eaf0; }
    [data-testid="stSidebar"] { background-color: #111318; border-right: 1px solid #2a2d35; }
    [data-testid="stMetric"] { background-color: #1a1d24; border: 1px solid #2a2d35; border-radius: 10px; padding: 16px; }
    [data-testid="stMetricValue"] { color: #00ff88 !important; }
    [data-testid="stMetricLabel"] { color: #6b7280 !important; }
    [data-testid="stChatMessage"] { background-color: #1a1d24; border: 1px solid #2a2d35; border-radius: 10px; margin-bottom: 8px; }
    .stButton button { background-color: #1a1d24; border: 1px solid #00ff88; color: #00ff88; border-radius: 8px; font-weight: 600; }
    .stButton button:hover { background-color: #00ff88; color: #0a0c10; }
    .basic-box { background: #1a1d24; border: 1px solid #2a2d35; border-top: 3px solid #6b7280; border-radius: 10px; padding: 20px; margin-bottom: 12px; }
    .advanced-box { background: #1a1d24; border: 1px solid #2a2d35; border-top: 3px solid #00ff88; border-radius: 10px; padding: 20px; margin-bottom: 12px; }
    .source-chip { display: inline-block; background: rgba(0,255,136,0.08); border: 1px solid rgba(0,255,136,0.2); color: #00ff88; padding: 2px 10px; border-radius: 100px; font-size: 11px; margin: 2px; font-family: monospace; }
    .basic-chip { display: inline-block; background: rgba(107,114,128,0.15); border: 1px solid rgba(107,114,128,0.3); color: #9ca3af; padding: 2px 10px; border-radius: 100px; font-size: 11px; margin: 2px; font-family: monospace; }
    .score-chip { display: inline-block; background: rgba(124,106,247,0.1); border: 1px solid rgba(124,106,247,0.2); color: #a78bfa; padding: 2px 10px; border-radius: 100px; font-size: 11px; margin: 2px; font-family: monospace; }
    .badge-green { background: rgba(0,255,136,0.1); border: 1px solid rgba(0,255,136,0.3); color: #00ff88; padding: 3px 12px; border-radius: 100px; font-size: 12px; font-weight: 600; }
    .badge-red { background: rgba(255,74,107,0.1); border: 1px solid rgba(255,74,107,0.3); color: #ff4a6b; padding: 3px 12px; border-radius: 100px; font-size: 12px; font-weight: 600; }
    .rewrite-box { background: rgba(0,255,136,0.05); border: 1px solid rgba(0,255,136,0.15); border-radius: 8px; padding: 12px; margin: 6px 0; font-size: 13px; font-family: monospace; color: #00ff88; }
    hr { border-color: #2a2d35; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

CHROMA_PATH = "chroma"
DATA_PATH   = "data"


@st.cache_resource
def get_chroma_client():
    try:
        return chromadb.PersistentClient(path=CHROMA_PATH)
    except:
        return None


def get_collection(client):
    try:
        cols = client.list_collections()
        return client.get_collection(cols[0].name) if cols else None
    except:
        return None


def get_ollama_models():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")[1:]
            models = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if parts:
                        models.append({"name": parts[0], "size": parts[2] if len(parts) > 2 else "?"})
            return models, True
        return [], False
    except:
        return [], False


def get_source_files(collection):
    try:
        results = collection.get(include=["metadatas"])
        sources = set()
        for meta in results["metadatas"]:
            source = meta.get("source", "")
            if source:
                sources.add(os.path.basename(source))
        return sorted(sources)
    except:
        return []


def run_basic_rag(question: str, k: int = 5):
    try:
        from query_data import query_rag
        from langchain_chroma import Chroma
        from get_embedding_function import get_embedding_function

        start = time.time()
        response = query_rag(question)
        elapsed = time.time() - start

        embedding_function = get_embedding_function()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
        results = db.similarity_search_with_score(question, k=k)
        sources = [doc.metadata.get("id", doc.metadata.get("source", "")) for doc, _ in results]
        scores  = [round(score, 3) for _, score in results]

        return {"response": response, "sources": sources, "scores": scores,
                "elapsed": round(elapsed, 1), "chunks_retrieved": k}
    except Exception as e:
        return {"response": f"Error: {e}", "sources": [], "scores": [], "elapsed": 0, "chunks_retrieved": 0}


def run_advanced_rag(question: str, strategy: str = "rewrite", k: int = 20, final_k: int = 5):
    try:
        from advanced_query import advanced_rag
        return advanced_rag(question=question, strategy=strategy,
                            retrieval_k=k, final_k=final_k, verbose=False)
    except Exception as e:
        return {"response": f"Error: {e}", "sources": [], "rerank_scores": [], "total_time": 0}


# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🍎 EarningsIQ")
    st.markdown("<p style='font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px'>Navigation</p>", unsafe_allow_html=True)
    page = st.radio("", ["⚡ Compare RAG Modes", "💬 Advanced Chat", "📊 Live Dashboard"], label_visibility="collapsed")

    st.divider()
    st.markdown("<p style='font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px'>System Status</p>", unsafe_allow_html=True)

    client = get_chroma_client()
    collection = get_collection(client) if client else None
    chunk_count = collection.count() if collection else 0
    if client and collection:
        st.markdown("🗄️ **ChromaDB** &nbsp; <span class='badge-green'>Connected</span>", unsafe_allow_html=True)
        st.caption(f"{chunk_count} chunks indexed")
    else:
        st.markdown("🗄️ **ChromaDB** &nbsp; <span class='badge-red'>Error</span>", unsafe_allow_html=True)

    models, ollama_ok = get_ollama_models()
    model_names = [m["name"] for m in models]
    if ollama_ok:
        st.markdown("🦙 **Ollama** &nbsp; <span class='badge-green'>Running</span>", unsafe_allow_html=True)
        for m in models:
            st.caption(f"  → {m['name']}")
    else:
        st.markdown("🦙 **Ollama** &nbsp; <span class='badge-red'>Offline</span>", unsafe_allow_html=True)

    st.markdown("🏆 **Cross-encoder** &nbsp; <span class='badge-green'>Cached</span>", unsafe_allow_html=True)
    st.caption("ms-marco-MiniLM-L-6-v2")

    st.divider()
    st.caption("Built by Md Kamruzzaman")
    st.caption("Advanced RAG · $0.00 · 100% Local")


# ══════════════════════════════════════════════════════════
# PAGE 1 — COMPARE RAG MODES
# ══════════════════════════════════════════════════════════
if page == "⚡ Compare RAG Modes":
    st.title("⚡ Basic vs Advanced RAG")
    st.caption("Same question · two pipelines · see the difference query rewriting + re-ranking makes")

    with st.expander("⚙️ Settings"):
        s1, s2, s3 = st.columns(3)
        with s1:
            strategy = st.selectbox("Rewriting strategy", ["rewrite", "multi", "hyde"],
                help="rewrite=simple · multi=3 phrasings (best for trends) · hyde=hypothetical answer")
        with s2:
            retrieval_k = st.slider("Retrieve k chunks", 10, 40, 20)
        with s3:
            final_k = st.slider("Keep after re-ranking", 3, 10, 5)

    st.divider()
    st.markdown("<p style='font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px'>These questions fail in basic RAG — try them</p>", unsafe_allow_html=True)

    suggestions = [
        "What was Apple revenue in Q4 FY2024?",
        "How did Apple Services revenue grow over the years?",
        "What was Apple gross margin in Q3 FY2023?",
        "How did iPhone revenue perform in FY2022?",
        "What did Tim Cook say about AI in FY2024?",
    ]
    scols = st.columns(5)
    for i, s in enumerate(suggestions):
        with scols[i]:
            if st.button(s[:30] + "...", key=f"sug_{i}", use_container_width=True):
                st.session_state["compare_q"] = s

    st.divider()
    question = st.text_input("Your question:",
        value=st.session_state.get("compare_q", ""),
        placeholder="What was Apple revenue in Q4 FY2024?")

    if st.button("🚀 Run Comparison", use_container_width=True) and question:
        st.session_state.pop("compare_q", None)

        col_b, col_a = st.columns(2)

        with col_b:
            st.markdown("### 🔘 Basic RAG")
            with st.spinner("Running basic pipeline..."):
                basic = run_basic_rag(question, k=5)

        with col_a:
            st.markdown("### ✅ Advanced RAG")
            with st.spinner(f"Rewriting ({strategy}) → retrieving → re-ranking..."):
                adv = run_advanced_rag(question, strategy=strategy, k=retrieval_k, final_k=final_k)

        with col_b:
            st.markdown(f"""<div class='basic-box'>
                <p style='font-size:11px;color:#6b7280;margin-bottom:8px'>BASIC · {basic.get('elapsed',0)}s · k=5 · no rewriting · no re-ranking</p>
                <p style='font-size:14px;line-height:1.7'>{basic['response']}</p>
            </div>""", unsafe_allow_html=True)
            if basic.get("sources"):
                chips = " ".join([f"<span class='basic-chip'>{os.path.basename(s)}</span>" for s in basic["sources"][:5]])
                st.markdown(f"**Sources:** {chips}", unsafe_allow_html=True)

        with col_a:
            adv_time = adv.get("total_time", 0)
            adv_chunks = adv.get("retrieval_count", retrieval_k)
            st.markdown(f"""<div class='advanced-box'>
                <p style='font-size:11px;color:#00ff88;margin-bottom:8px'>ADVANCED · {adv_time}s · {adv_chunks} chunks → re-ranked to {final_k} · strategy={strategy}</p>
                <p style='font-size:14px;line-height:1.7'>{adv['response']}</p>
            </div>""", unsafe_allow_html=True)
            if adv.get("sources"):
                chips = " ".join([f"<span class='source-chip'>{os.path.basename(s)}</span>" for s in adv["sources"][:5]])
                st.markdown(f"**Sources:** {chips}", unsafe_allow_html=True)
            if adv.get("rerank_scores"):
                scores = " ".join([f"<span class='score-chip'>{s}</span>" for s in adv["rerank_scores"]])
                st.markdown(f"**Re-rank scores:** {scores}", unsafe_allow_html=True)

        # Rewrite details
        st.divider()
        st.markdown("**Query rewriting — what the system searched for:**")
        if adv.get("rewritten_query"):
            st.markdown(f"<div class='rewrite-box'>→ {adv['rewritten_query']}</div>", unsafe_allow_html=True)
        elif adv.get("rewritten_queries"):
            for q in adv["rewritten_queries"]:
                st.markdown(f"<div class='rewrite-box'>→ {q}</div>", unsafe_allow_html=True)
        elif adv.get("hypothetical_doc"):
            st.markdown(f"<div class='rewrite-box'>HyDE: {adv['hypothetical_doc'][:300]}...</div>", unsafe_allow_html=True)

        # Timing
        if adv.get("rewrite_time"):
            st.divider()
            st.markdown("**Advanced RAG timing breakdown:**")
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("✏️ Rewrite", f"{adv.get('rewrite_time',0)}s")
            t2.metric("🗄️ Retrieval", f"{adv.get('retrieval_time',0)}s")
            t3.metric("🏆 Re-rank", f"{adv.get('rerank_time',0)}s")
            t4.metric("🌪️ Generation", f"{adv.get('generation_time',0)}s")


# ══════════════════════════════════════════════════════════
# PAGE 2 — ADVANCED CHAT
# ══════════════════════════════════════════════════════════
elif page == "💬 Advanced Chat":
    st.title("💬 Advanced RAG Chat")
    st.caption("Every question runs through query rewriting + cross-encoder re-ranking")

    with st.expander("⚙️ Settings"):
        c1, c2, c3 = st.columns(3)
        with c1:
            chat_strategy = st.selectbox("Strategy", ["rewrite", "multi", "hyde"])
        with c2:
            chat_k = st.slider("Retrieve k", 10, 40, 20)
        with c3:
            chat_final_k = st.slider("Keep after re-rank", 3, 10, 5)

    st.divider()
    st.markdown("<p style='font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px'>Suggested Questions</p>", unsafe_allow_html=True)
    chat_suggestions = [
        "What was Apple total revenue in Q4 FY2024?",
        "How did Apple Services revenue grow over the years?",
        "What was Apple gross margin percentage in 2023?",
        "How did iPhone revenue perform during 2022?",
        "How much cash did Apple return to shareholders?",
        "What was the highest revenue quarter for Apple?",
    ]
    chat_cols = st.columns(3)
    for i, s in enumerate(chat_suggestions):
        with chat_cols[i % 3]:
            if st.button(s, key=f"cs_{i}", use_container_width=True):
                st.session_state["chat_prefill"] = s

    st.divider()

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                chips = " ".join([f"<span class='source-chip'>{s}</span>" for s in msg["sources"]])
                st.markdown(f"**Sources:** {chips}", unsafe_allow_html=True)
            if msg.get("scores"):
                sc = " ".join([f"<span class='score-chip'>{s}</span>" for s in msg["scores"]])
                st.markdown(f"**Re-rank scores:** {sc}", unsafe_allow_html=True)
            if msg.get("meta"):
                st.caption(msg["meta"])

    prefill = st.session_state.pop("chat_prefill", None)
    question = st.chat_input("Ask anything about Apple earnings...")
    if prefill and not question:
        question = prefill

    if question:
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_messages.append({"role": "user", "content": question})

        with st.chat_message("assistant"):
            with st.spinner(f"Rewriting ({chat_strategy}) → {chat_k} chunks → re-ranking → Mistral..."):
                result = run_advanced_rag(question, strategy=chat_strategy, k=chat_k, final_k=chat_final_k)

            st.markdown(result["response"])
            clean_sources = [os.path.basename(s) for s in result.get("sources", [])[:5]]
            scores = result.get("rerank_scores", [])

            if clean_sources:
                chips = " ".join([f"<span class='source-chip'>{s}</span>" for s in clean_sources])
                st.markdown(f"**Sources:** {chips}", unsafe_allow_html=True)
            if scores:
                sc = " ".join([f"<span class='score-chip'>{s}</span>" for s in scores])
                st.markdown(f"**Re-rank scores:** {sc}", unsafe_allow_html=True)

            meta = f"⏱️ {result.get('total_time',0)}s · strategy={chat_strategy} · retrieved={result.get('retrieval_count', chat_k)} → kept={chat_final_k}"
            st.caption(meta)

        st.session_state.chat_messages.append({
            "role": "assistant", "content": result["response"],
            "sources": clean_sources, "scores": scores, "meta": meta
        })

    if st.session_state.chat_messages:
        if st.button("🗑️ Clear conversation"):
            st.session_state.chat_messages = []
            st.rerun()


# ══════════════════════════════════════════════════════════
# PAGE 3 — DASHBOARD
# ══════════════════════════════════════════════════════════
elif page == "📊 Live Dashboard":
    st.title("📊 System Dashboard")
    st.caption("Live stats from ChromaDB and Ollama")

    col_h, col_btn = st.columns([5, 1])
    with col_btn:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()

    st.divider()

    source_files = get_source_files(collection) if collection else []
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("📦 Chunks", chunk_count)
    m2.metric("📄 PDFs", len(source_files))
    m3.metric("🦙 Models", len(models))
    m4.metric("🔄 Strategies", "3")
    m5.metric("💰 Cost", "$0.00")
    m6.metric("🔒 Privacy", "100% Local")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.markdown("### 🔧 Components")
        comps = [
            ("🦙","Ollama","v0.21.1","Running" if ollama_ok else "Offline", ollama_ok),
            ("🌪️","Mistral 7B","4.4 GB · LLM","Loaded" if any("mistral" in m.lower() for m in model_names) else "Not loaded", any("mistral" in m.lower() for m in model_names)),
            ("🔢","nomic-embed-text","274 MB · embedder","Loaded" if any("nomic" in m.lower() for m in model_names) else "Not loaded", any("nomic" in m.lower() for m in model_names)),
            ("🏆","Cross-encoder re-ranker","ms-marco-MiniLM-L-6-v2","Cached locally", True),
            ("🗄️","ChromaDB","v1.5.8","Connected" if collection else "Error", collection is not None),
            ("🔗","LangChain","v1.2.15","Active", True),
        ]
        for icon,name,detail,status,ok in comps:
            ci,cb = st.columns([3,1])
            with ci:
                st.markdown(f"**{icon} {name}**")
                st.caption(detail)
            with cb:
                badge = "badge-green" if ok else "badge-red"
                st.markdown(f"<span class='{badge}'>{status}</span>", unsafe_allow_html=True)
            st.divider()

    with right:
        st.markdown("### 🆕 Advanced RAG Features")
        feats = [
            ("✏️","Simple query rewriting","Rewrites into Apple press release language"),
            ("📋","Multi-query (3 phrasings)","Wider retrieval pool for trend questions"),
            ("🧠","HyDE","Hypothetical answer as search vector"),
            ("🏆","Cross-encoder re-ranking","Scores query+chunk pairs for precision"),
            ("📊","Re-rank confidence scores","Visible per-chunk relevance scores"),
            ("⚡","Basic vs Advanced compare","Side-by-side pipeline comparison"),
        ]
        for icon,name,detail in feats:
            fi,fb = st.columns([3,1])
            with fi:
                st.markdown(f"**{icon} {name}**")
                st.caption(detail)
            with fb:
                st.markdown("<span class='badge-green'>Active</span>", unsafe_allow_html=True)
            st.divider()

    st.markdown("### ⚙️ Advanced RAG Pipeline")
    steps = [("❓","Question","as typed"),("✏️","Rewriter","3 strategies"),
             ("🔢","Embed","nomic"),("🗄️","Retrieve","top-20 pool"),
             ("🏆","Re-rank","cross-encoder"),("📋","Inject","best 5"),
             ("🌪️","Mistral","generate"),("✅","Answer","+ scores")]
    pipe_cols = st.columns(8)
    for col,(icon,name,detail) in zip(pipe_cols,steps):
        with col:
            st.markdown(f"""<div style='text-align:center;background:#1a1d24;border:1px solid
            #2a2d35;border-radius:8px;padding:10px;'>
            <div style='font-size:20px'>{icon}</div>
            <div style='font-size:11px;font-weight:600;margin-top:4px'>{name}</div>
            <div style='font-size:10px;color:#6b7280'>{detail}</div></div>""",
            unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🔍 ChromaDB Chunk Explorer")
    if collection:
        sel = st.selectbox("Inspect chunks from:", ["All documents"] + (source_files if source_files else []))
        if sel == "All documents":
            res = collection.get(limit=8, include=["documents","metadatas"])
        else:
            res = collection.get(where={"source":{"$eq":f"data\\{sel}"}},
                                 limit=8, include=["documents","metadatas"])
        for i,(doc,meta) in enumerate(zip(res["documents"], res["metadatas"])):
            with st.expander(f"Chunk {i+1} — {meta.get('source','?')} · page {meta.get('page','?')}"):
                st.text(doc[:500]+"..." if len(doc)>500 else doc)
                st.caption(str(meta))
    else:
        st.error("ChromaDB not connected.")
