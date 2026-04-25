"""
Apple Earnings RAG — Full Web App
===================================
A Streamlit web app with two pages:
  1. 💬 Ask Questions  — query your RAG system from the browser
  2. 📊 Dashboard      — live stats from ChromaDB and Ollama

Usage:
    pip install streamlit
    streamlit run app.py
"""

import streamlit as st
import chromadb
import subprocess
import time
import sys
import os

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Apple Earnings RAG",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0a0c10; color: #e8eaf0; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #111318;
        border-right: 1px solid #2a2d35;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #1a1d24;
        border: 1px solid #2a2d35;
        border-radius: 10px;
        padding: 16px;
    }
    [data-testid="stMetricValue"] { color: #00ff88 !important; }
    [data-testid="stMetricLabel"] { color: #6b7280 !important; }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background-color: #1a1d24;
        border: 1px solid #2a2d35;
        border-radius: 10px;
        margin-bottom: 8px;
    }

    /* Input box */
    [data-testid="stChatInput"] textarea {
        background-color: #1a1d24 !important;
        border: 1px solid #2a2d35 !important;
        color: #e8eaf0 !important;
    }

    /* Buttons */
    .stButton button {
        background-color: #1a1d24;
        border: 1px solid #00ff88;
        color: #00ff88;
        border-radius: 8px;
    }
    .stButton button:hover {
        background-color: #00ff88;
        color: #0a0c10;
    }

    /* Source chips */
    .source-chip {
        display: inline-block;
        background: rgba(0,255,136,0.08);
        border: 1px solid rgba(0,255,136,0.2);
        color: #00ff88;
        padding: 2px 10px;
        border-radius: 100px;
        font-size: 11px;
        margin: 2px;
        font-family: monospace;
    }

    /* Section headers */
    .section-header {
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #6b7280;
        margin-bottom: 12px;
    }

    /* Status badge */
    .badge-green {
        background: rgba(0,255,136,0.1);
        border: 1px solid rgba(0,255,136,0.3);
        color: #00ff88;
        padding: 3px 12px;
        border-radius: 100px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-red {
        background: rgba(255,74,107,0.1);
        border: 1px solid rgba(255,74,107,0.3);
        color: #ff4a6b;
        padding: 3px 12px;
        border-radius: 100px;
        font-size: 12px;
        font-weight: 600;
    }

    /* Divider */
    hr { border-color: #2a2d35; }

    /* Dataframe */
    [data-testid="stDataFrame"] { background-color: #1a1d24; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────
CHROMA_PATH = "chroma"
DATA_PATH   = "data"

# ── Helper functions ───────────────────────────────────────────

@st.cache_resource
def get_chroma_client():
    """Connect to ChromaDB — cached so it only connects once."""
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        return client
    except Exception as e:
        return None


def get_collection(client):
    """Get the first collection from ChromaDB."""
    try:
        collections = client.list_collections()
        if collections:
            return client.get_collection(collections[0].name)
        return None
    except:
        return None


def get_ollama_models():
    """Get list of models loaded in Ollama."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")[1:]  # skip header
            models = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if parts:
                        models.append({
                            "name": parts[0],
                            "size": parts[2] if len(parts) > 2 else "?",
                            "unit": parts[3] if len(parts) > 3 else ""
                        })
            return models, True
        return [], False
    except:
        return [], False


def get_source_files(collection):
    """Get unique source PDF files from ChromaDB metadata."""
    try:
        results = collection.get(include=["metadatas"])
        sources = set()
        for meta in results["metadatas"]:
            source = meta.get("source", "")
            if source:
                # Extract just filename
                filename = os.path.basename(source)
                sources.add(filename)
        return sorted(sources)
    except:
        return []


def query_rag(question: str, k: int = 5):
    """Run a RAG query and return response + sources."""
    try:
        # Import here to avoid circular issues
        from query_data import query_rag as _query_rag
        # Temporarily patch k value
        import query_data
        original_k = 5

        # Run the query
        start = time.time()
        response = _query_rag(question)
        elapsed = time.time() - start

        # Get sources separately
        from langchain_ollama import OllamaEmbeddings
        from langchain_chroma import Chroma
        from get_embedding_function import get_embedding_function

        embedding_function = get_embedding_function()
        db = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embedding_function
        )
        results = db.similarity_search_with_score(question, k=k)
        sources = [doc.metadata.get("id", doc.metadata.get("source", "")) for doc, _ in results]
        scores  = [round(score, 3) for _, score in results]

        return response, sources, scores, elapsed
    except Exception as e:
        return f"Error: {e}", [], [], 0


# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🍎 Apple RAG")
    st.markdown("<p class='section-header'>Navigation</p>", unsafe_allow_html=True)

    page = st.radio(
        "",
        ["💬 Ask Questions", "📊 Live Dashboard"],
        label_visibility="collapsed"
    )

    st.divider()

    # Quick system status in sidebar
    st.markdown("<p class='section-header'>System Status</p>", unsafe_allow_html=True)

    # ChromaDB status
    client = get_chroma_client()
    if client:
        collection = get_collection(client)
        if collection:
            chunk_count = collection.count()
            st.markdown(f"🗄️ **ChromaDB** &nbsp; <span class='badge-green'>Connected</span>", unsafe_allow_html=True)
            st.caption(f"{chunk_count} chunks indexed")
        else:
            st.markdown("🗄️ **ChromaDB** &nbsp; <span class='badge-red'>No collection</span>", unsafe_allow_html=True)
    else:
        st.markdown("🗄️ **ChromaDB** &nbsp; <span class='badge-red'>Error</span>", unsafe_allow_html=True)

    # Ollama status
    models, ollama_ok = get_ollama_models()
    if ollama_ok:
        st.markdown(f"🦙 **Ollama** &nbsp; <span class='badge-green'>Running</span>", unsafe_allow_html=True)
        for m in models:
            st.caption(f"  → {m['name']}")
    else:
        st.markdown("🦙 **Ollama** &nbsp; <span class='badge-red'>Not running</span>", unsafe_allow_html=True)

    st.divider()
    st.caption("Built by Md Kamruzzaman")
    st.caption("Local RAG · No API cost · Private")


# ══════════════════════════════════════════════════════════════
# PAGE 1 — ASK QUESTIONS
# ══════════════════════════════════════════════════════════════
if page == "💬 Ask Questions":

    st.title("💬 Ask Apple Earnings Questions")
    st.caption("Powered by Mistral 7B + ChromaDB · Running 100% locally")

    # Settings expander
    with st.expander("⚙️ Query Settings"):
        k_value = st.slider(
            "Number of chunks to retrieve (k)",
            min_value=3, max_value=15, value=5,
            help="Higher k = more context but slower. Try 10 for trend questions."
        )
        st.caption("💡 Use k=10 for questions about trends across multiple quarters")

    st.divider()

    # Suggested questions
    st.markdown("<p class='section-header'>Suggested Questions</p>", unsafe_allow_html=True)

    suggestions = [
        "What was Apple revenue in the September quarter 2024?",
        "What did Tim Cook say about artificial intelligence?",
        "What was Apple gross margin percentage in 2023?",
        "How did iPhone revenue perform in 2022?",
        "What was Apple Services revenue all time record?",
        "How much cash did Apple return to shareholders?",
    ]

    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                st.session_state["prefill_question"] = suggestion

    st.divider()

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                sources_html = " ".join([f"<span class='source-chip'>{s}</span>" for s in msg["sources"][:5]])
                st.markdown(f"**Sources:** {sources_html}", unsafe_allow_html=True)
            if msg.get("time"):
                st.caption(f"⏱️ {msg['time']:.1f}s · k={msg.get('k', 5)} chunks retrieved")

    # Handle prefilled question from suggestion buttons
    prefill = st.session_state.pop("prefill_question", None)

    # Chat input
    question = st.chat_input("Ask anything about Apple earnings...")

    # Use prefill if button was clicked
    if prefill and not question:
        question = prefill

    if question:
        # Show user message
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.messages.append({"role": "user", "content": question})

        # Get RAG response
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching ChromaDB → 🌪️ Mistral thinking..."):
                response, sources, scores, elapsed = query_rag(question, k=k_value)

            st.markdown(response)

            if sources:
                # Clean up source names
                clean_sources = []
                for s in sources[:5]:
                    name = os.path.basename(s) if s else s
                    name = name.replace("data\\", "").replace("data/", "")
                    clean_sources.append(name)

                sources_html = " ".join([f"<span class='source-chip'>{s}</span>" for s in clean_sources])
                st.markdown(f"**Sources:** {sources_html}", unsafe_allow_html=True)

            st.caption(f"⏱️ {elapsed:.1f}s · k={k_value} chunks retrieved")

        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "sources": clean_sources if sources else [],
            "time": elapsed,
            "k": k_value
        })

    # Clear chat button
    if st.session_state.messages:
        if st.button("🗑️ Clear conversation"):
            st.session_state.messages = []
            st.rerun()


# ══════════════════════════════════════════════════════════════
# PAGE 2 — LIVE DASHBOARD
# ══════════════════════════════════════════════════════════════
elif page == "📊 Live Dashboard":

    st.title("📊 RAG System Dashboard")
    st.caption("Live stats from your local ChromaDB and Ollama")

    # Refresh button
    col_title, col_btn = st.columns([4, 1])
    with col_btn:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()

    st.divider()

    # ── Top metrics ──────────────────────────────────────────
    client = get_chroma_client()
    collection = get_collection(client) if client else None
    models, ollama_ok = get_ollama_models()

    chunk_count  = collection.count() if collection else 0
    source_files = get_source_files(collection) if collection else []
    model_names  = [m["name"] for m in models]

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📦 Chunks in DB", chunk_count)
    with col2:
        st.metric("📄 PDFs Indexed", len(source_files))
    with col3:
        st.metric("🦙 Ollama Models", len(models))
    with col4:
        st.metric("💰 Cost", "$0.00")
    with col5:
        st.metric("🔒 Privacy", "100% Local")

    st.divider()

    # ── Two column layout ────────────────────────────────────
    left, right = st.columns(2)

    with left:
        # Component status
        st.markdown("### 🔧 Components")

        components = [
            ("🦙", "Ollama", "v0.21.1 · local LLM server",
             "Running" if ollama_ok else "Offline", ollama_ok),
            ("🌪️", "Mistral 7B", "4.4 GB · generation model",
             "Loaded" if any("mistral" in m.lower() for m in model_names) else "Not loaded",
             any("mistral" in m.lower() for m in model_names)),
            ("🔢", "nomic-embed-text", "274 MB · embedding model",
             "Loaded" if any("nomic" in m.lower() for m in model_names) else "Not loaded",
             any("nomic" in m.lower() for m in model_names)),
            ("🗄️", "ChromaDB", f"v1.5.8 · {chunk_count} chunks",
             "Connected" if collection else "Error", collection is not None),
            ("🔗", "LangChain", "v1.2.15 · orchestration",
             "Active", True),
            ("🐍", "Python", f"{sys.version.split()[0]}",
             "Running", True),
        ]

        for icon, name, detail, status, is_ok in components:
            col_info, col_badge = st.columns([3, 1])
            with col_info:
                st.markdown(f"**{icon} {name}**")
                st.caption(detail)
            with col_badge:
                badge_class = "badge-green" if is_ok else "badge-red"
                st.markdown(
                    f"<span class='{badge_class}'>{status}</span>",
                    unsafe_allow_html=True
                )
            st.divider()

    with right:
        # Indexed documents
        st.markdown("### 📄 Indexed Documents")

        if source_files:
            for f in source_files:
                # Parse filename for display
                name = f.replace(".pdf", "").replace("apple_", "").upper()
                parts = name.split("_")
                if len(parts) >= 3:
                    label = f"🍎 {parts[0]} {parts[1]} · {parts[2]}"
                else:
                    label = f"🍎 {name}"
                st.caption(label)
        else:
            st.warning("No documents found. Run populate_database.py first.")

    st.divider()

    # ── Pipeline flow ────────────────────────────────────────
    st.markdown("### ⚙️ RAG Pipeline")

    p1, p2, p3, p4, p5, p6, p7, p8 = st.columns(8)
    steps = [
        ("📄", "PDFs", f"{len(source_files)} files"),
        ("✂️", "Chunker", "800 chars"),
        ("🔢", "Embedder", "nomic-embed"),
        ("🗄️", "ChromaDB", f"{chunk_count} vectors"),
        ("❓", "Query", "your question"),
        ("🎯", "Retrieve", "top-k chunks"),
        ("🌪️", "Mistral", "generates"),
        ("✅", "Answer", "+ sources"),
    ]
    for col, (icon, name, detail) in zip(
        [p1,p2,p3,p4,p5,p6,p7,p8], steps
    ):
        with col:
            st.markdown(
                f"""<div style='text-align:center; background:#1a1d24;
                border:1px solid #2a2d35; border-radius:8px; padding:10px;'>
                <div style='font-size:22px'>{icon}</div>
                <div style='font-size:11px; font-weight:600; margin-top:4px'>{name}</div>
                <div style='font-size:10px; color:#6b7280'>{detail}</div>
                </div>""",
                unsafe_allow_html=True
            )

    st.divider()

    # ── ChromaDB chunk explorer ──────────────────────────────
    st.markdown("### 🔍 ChromaDB Chunk Explorer")

    if collection:
        selected_file = st.selectbox(
            "Select a document to inspect its chunks:",
            ["All documents"] + source_files
        )

        if selected_file == "All documents":
            results = collection.get(
                limit=10,
                include=["documents", "metadatas"]
            )
        else:
            results = collection.get(
                where={"source": {"$eq": f"data\\{selected_file}"}},
                limit=10,
                include=["documents", "metadatas"]
            )

        if results["documents"]:
            for i, (doc, meta) in enumerate(
                zip(results["documents"], results["metadatas"])
            ):
                with st.expander(f"Chunk {i+1} — {meta.get('source', 'unknown')} · page {meta.get('page', '?')}"):
                    st.text(doc[:500] + "..." if len(doc) > 500 else doc)
                    st.caption(f"Metadata: {meta}")
        else:
            st.info("No chunks found for this document.")
    else:
        st.error("ChromaDB not connected. Run populate_database.py first.")

    st.divider()

    # ── System info ──────────────────────────────────────────
    st.markdown("### 💻 Environment")

    env_col1, env_col2 = st.columns(2)
    with env_col1:
        st.markdown("**Python packages:**")
        packages = [
            "langchain", "langchain_community",
            "langchain_chroma", "langchain_ollama",
            "chromadb", "pypdf", "streamlit"
        ]
        for pkg in packages:
            try:
                mod = __import__(pkg)
                version = getattr(mod, "__version__", "✓")
                st.caption(f"✅ {pkg} {version}")
            except ImportError:
                st.caption(f"❌ {pkg} not found")

    with env_col2:
        st.markdown("**Ollama models:**")
        if models:
            for m in models:
                st.caption(f"✅ {m['name']} · {m['size']} {m['unit']}")
        else:
            st.caption("❌ No models found or Ollama not running")

        st.markdown("**Paths:**")
        st.caption(f"📁 Data: ./{DATA_PATH}/")
        st.caption(f"🗄️ ChromaDB: ./{CHROMA_PATH}/")
        st.caption(f"🐍 Python: {sys.executable}")