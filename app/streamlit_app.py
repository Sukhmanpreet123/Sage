"""
app/streamlit_app.py
--------------------
Sage — Multi-Agent Research Intelligence System
2026 PREMIUM Edition: Full feature set including:
  - Research History Dashboard
  - Agent Performance Analytics (Plotly charts)
  - Source Credibility Badges
  - Topic Auto-Suggestions with Trending Topics
  - Markdown + Word + PDF export
  - Typewriter streaming animation for report
  - Multi-Topic Comparison Mode
  - HITL checkpoint UI
"""

import streamlit as st
import time
import os
import sys
import uuid
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graph.workflow import build_research_graph, make_initial_state
from tools.history_manager import load_history, clear_history
from tools.topic_suggestions import (
    get_suggestions, get_random_topic, get_all_domains,
    get_random_topic_by_domain, TRENDING_TOPICS
)

@st.cache_resource
def get_cached_graph():
    return build_research_graph(use_checkpointer=True)

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sage • Multi-Agent Research Intelligence System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Premium CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; font-weight: 700; }

.stApp {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #f1f5f9 100%);
    color: #0f172a;
}
section[data-testid="stSidebar"] {
    background-color: #f8fafc !important;
    border-right: 1px solid #e2e8f0;
    backdrop-filter: blur(12px);
}
section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] p {
    color: #0f172a !important;
}
section[data-testid="stSidebar"] label {
    color: #334155 !important;
    font-weight: 600;
}
div[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05);
    transition: transform 0.25s ease, border-color 0.25s ease;
    color: #0f172a !important;
}
div[data-testid="metric-container"] div {
    color: #0f172a !important;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-3px);
    border-color: #3b82f6;
}
.main-title {
    font-size: 3.2rem;
    background: linear-gradient(135deg, #0f172a, #3b82f6, #0f766e);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.04em;
    line-height: 1.1;
}
.glass-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 18px;
    backdrop-filter: blur(8px);
    box-shadow: 0 8px 32px rgba(15, 23, 42, 0.06);
    color: #0f172a;
}
.glass-card p, .glass-card span, .glass-card li, .glass-card div {
    color: #334155;
}
.hitl-card {
    background: rgba(234,179,8,0.06);
    border: 1px solid rgba(234,179,8,0.35);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 18px;
    animation: pulse-border 2s infinite;
}
@keyframes pulse-border {
    0%   { border-color: rgba(234,179,8,0.3); box-shadow: 0 0 0 0 rgba(234,179,8,0.1); }
    50%  { border-color: rgba(234,179,8,0.7); box-shadow: 0 0 20px rgba(234,179,8,0.15); }
    100% { border-color: rgba(234,179,8,0.3); box-shadow: 0 0 0 0 rgba(234,179,8,0.1); }
}
.cred-badge-high   { background: rgba(16,185,129,0.15); color: #10b981; padding: 2px 9px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid rgba(16,185,129,0.3); }
.cred-badge-medium { background: rgba(245,158,11,0.15); color: #f59e0b; padding: 2px 9px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid rgba(245,158,11,0.3); }
.cred-badge-low    { background: rgba(239,68,68,0.15);  color: #ef4444; padding: 2px 9px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid rgba(239,68,68,0.3); }
.source-type-arxiv { color: #3b82f6; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.source-type-wiki  { color: #10b981; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.source-type-web   { color: #64748b; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.source-type-news  { color: #fb923c; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.source-type-pubmed { color: #ec4899; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.source-type-openalex { color: #8b5cf6; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.activity-node {
    border-left: 2px solid #3b82f6;
    padding-left: 14px;
    margin-left: 4px;
    margin-bottom: 12px;
    position: relative;
    color: #334155;
}
.activity-node::before {
    content: '';
    position: absolute;
    left: -6px; top: 4px;
    width: 9px; height: 9px;
    border-radius: 50%;
    background: #0f766e;
    box-shadow: 0 0 8px rgba(15, 118, 110, 0.4);
}
.history-item {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    color: #0f172a;
}
.history-item:hover {
    border-color: #3b82f6;
    background: rgba(59, 130, 246, 0.04);
}
.score-ring {
    width: 80px; height: 80px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; font-weight: 800;
    margin: 0 auto 8px auto;
}
div.stButton > button:first-child {
    background: linear-gradient(135deg, #0f172a, #3b82f6) !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 11px 24px !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2) !important;
    transition: all 0.25s ease !important;
    width: 100%;
}
div.stButton > button:first-child:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(15, 23, 42, 0.3) !important;
}
div[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #0f766e, #0d9488) !important;
    color: white !important; border: none !important;
    font-weight: 600 !important; border-radius: 10px !important;
    padding: 10px 20px !important;
    box-shadow: 0 4px 15px rgba(15, 118, 110, 0.2) !important;
    transition: all 0.25s ease !important;
    width: 100%;
}
div[data-testid="stDownloadButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(13, 148, 136, 0.3) !important;
}
.tag-pill {
    display: inline-block;
    background: rgba(59, 130, 246, 0.08);
    border: 1px solid rgba(59, 130, 246, 0.2);
    color: #3b82f6;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    margin: 2px 3px;
    cursor: pointer;
    transition: all 0.2s;
}
.tag-pill:hover { background: rgba(59, 130, 246, 0.15); }
.comparison-col {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 20px;
    height: 100%;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
col_hdr, col_badge = st.columns([5, 1])
with col_hdr:
    st.markdown("<h1 class='main-title'>Sage 🧠</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:1.1rem; color:#475569; font-weight:300; margin-top:-8px;'>"
        "Production-Grade Multi-Agent Research Engine &nbsp;•&nbsp; "
        "LangGraph Orchestration &nbsp;•&nbsp; 100% Free Stack"
        "</p>",
        unsafe_allow_html=True
    )
with col_badge:
    st.markdown(
        "<div style='text-align:right; padding-top:16px;'>"
        "<span style='background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.2); "
        "color:#3b82f6; padding:5px 14px; border-radius:20px; font-size:0.82rem; font-weight:600;'>"
        "2026 Edition</span></div>",
        unsafe_allow_html=True
    )
st.divider()

# ── Session State Init ────────────────────────────────────────────────────────
_defaults = {
    "thread_id":        str(uuid.uuid4()),
    "hitl_pending":     False,
    "partial_state":    None,
    "events_log":       [],
    "graph":            None,
    "result":           None,
    "compare_result_a": None,
    "compare_result_b": None,
    "topic_a":          "",
    "topic_b":          "",
    "active_tab":       "research",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand
    st.markdown(
        "<h2 style='color:#a855f7; font-size:1.5rem; margin-bottom:2px;'>⚙️ Control Center</h2>"
        "<p style='color:#64748b; font-size:0.82rem; margin-top:0;'>Configure your research pipeline</p>",
        unsafe_allow_html=True
    )
    st.divider()

    # Tabs inside sidebar
    sidebar_tab = st.radio(
        "Panel",
        ["🔬 Config", "📜 History", "🕵️ Agents"],
        horizontal=True, label_visibility="collapsed"
    )

    st.divider()

    if sidebar_tab == "🔬 Config":
        # LLM provider
        model_choice = st.selectbox(
            "LLM Provider",
            [
                "⚡ Groq Cloud — Ultra-Fast Free API (Llama 4)",
                "✨ Google Gemini — Free API (Gemini 2.0 Flash)",
                "🦙 Ollama — Local (Llama 4 / Gemma 4)",
            ],
            index=0,
            help="Groq is recommended for best speed + quality balance."
        )
        llm_type = "ollama"
        if "Groq"   in model_choice: llm_type = "groq"
        elif "Gemini" in model_choice: llm_type = "gemini"

        default_model_map = {
            "ollama": "llama4:scout",
            "groq":   "llama-4-scout-17b-16e-instruct",
            "gemini": "gemini-2.0-flash"
        }
        model_name_override = st.text_input(
            "Model Override (optional)",
            value="",
            placeholder=f"Default: {default_model_map[llm_type]}",
            help="Leave blank for auto-selection."
        )
        model_name = model_name_override.strip() or None

        st.divider()

        st.markdown("<h4 style='color:#0f172a; margin-bottom:4px;'>🧑‍💼 Human-in-the-Loop</h4>", unsafe_allow_html=True)
        hitl_enabled = st.toggle("Enable HITL Checkpoint", value=True,
            help="Pauses after Fact Checker for human review of verified claims.")
        if hitl_enabled:
            st.markdown(
                "<div style='font-size:0.8rem; color:#fbbf24; background:rgba(251,191,36,0.07); "
                "padding:7px 11px; border-radius:8px;'>⏸️ Pipeline pauses for your approval.</div>",
                unsafe_allow_html=True
            )

        st.divider()

        # Compare Mode
        st.markdown("<h4 style='color:#0f172a; margin-bottom:4px;'>⚖️ Compare Mode</h4>", unsafe_allow_html=True)
        compare_mode = st.toggle("Enable Multi-Topic Comparison",
            help="Research two topics simultaneously and see a side-by-side comparison.")

        st.divider()

        # Session
        st.markdown("<h4 style='color:#0f172a; margin-bottom:4px;'>🔖 Session</h4>", unsafe_allow_html=True)
        st.code(st.session_state.thread_id[:8] + "...", language=None)
        if st.button("🔄 New Session"):
            for k, v in _defaults.items():
                st.session_state[k] = v
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()

    elif sidebar_tab == "📜 History":
        st.markdown("<h4 style='color:#0f172a;'>📜 Research History</h4>", unsafe_allow_html=True)
        history = load_history()
        if not history:
            st.info("No research runs yet. Run your first topic!")
        else:
            st.caption(f"{len(history)} run(s) stored")
            for run in history[:10]:
                score = run.get("quality_score", 0)
                s_color = "#10b981" if score >= 80 else "#f59e0b" if score >= 70 else "#ef4444"
                st.markdown(
                    f"<div class='history-item'>"
                    f"<div style='font-size:0.88rem; font-weight:600; color:#0f172a; "
                    f"white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>"
                    f"🔍 {run['topic'][:40]}{'…' if len(run['topic']) > 40 else ''}</div>"
                    f"<div style='font-size:0.75rem; color:#64748b; margin-top:3px;'>"
                    f"{run.get('date_display','?')} &nbsp;•&nbsp; "
                    f"<span style='color:{s_color}; font-weight:600;'>{score}/100</span> &nbsp;•&nbsp; "
                    f"{run.get('verified_count',0)} claims &nbsp;•&nbsp; {run.get('llm_type','?').upper()}"
                    f"</div></div>",
                    unsafe_allow_html=True
                )
            if st.button("🗑️ Clear All History"):
                clear_history()
                st.rerun()

    else:  # Agents tab
        st.markdown("<h4 style='color:#0f172a;'>🕵️ Agent Pipeline</h4>", unsafe_allow_html=True)
        agents_info = [
            ("🗄️", "Cache Check",             "ChromaDB semantic RAG — skips live search if similar topic found"),
            ("🔍", "Researcher",              "Web + Wikipedia (full extracts) + ArXiv Deep Mode + RSS News"),
            ("🛡️", "Fact Checker",            "Cross-references all claims, removes hallucinations, scores confidence"),
            ("⚡", "Contradiction Detector",  "[Phase 2] Flags conflicts between claims & your personal library"),
            ("⏸️", "HITL Review",             "Human approval checkpoint — you review & guide before writing"),
            ("📊", "Analyst",                 "Extracts statistics, trends, comparisons & strategic implications"),
            ("🔬", "Gap Detector",            "[Phase 1] Identifies open questions, limitations & future directions"),
            ("✍️", "Writer",                  "11-section structured report with 2500+ words + gap integration"),
            ("🧐", "Critic",                  "Quality gate — rejects drafts scoring below 70/100 (max 3 retries)"),
        ]
        for icon, name, desc in agents_info:
            color = "#8b5cf6" if "Phase" in desc else "#3b82f6"
            st.markdown(
                f"<div style='margin-bottom:10px;'>"
                f"<span style='font-weight:600; color:{color};'>{icon} {name}</span><br>"
                f"<span style='font-size:0.78rem; color:#64748b;'>{desc}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

# ── Research Library Sidebar (Phase 2 Feature 5) ─────────────────────────────
with st.sidebar:
    st.divider()
    with st.expander("📚 My Research Library", expanded=False):
        st.markdown(
            "<span style='font-size:0.82rem; color:#64748b;'>"
            "Upload your own research PDFs. The system will index them and "
            "cross-reference against new findings to detect contradictions."
            "</span>",
            unsafe_allow_html=True
        )
        try:
            from tools.library_manager import (
                index_user_pdf, list_library_documents,
                delete_from_library, get_library_count
            )
            chunk_count = get_library_count()
            doc_list    = list_library_documents()
            if chunk_count > 0:
                st.markdown(
                    f"<div style='background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2); "
                    f"border-radius:8px; padding:7px 12px; margin-bottom:10px;'>"
                    f"<span style='color:#10b981; font-size:0.82rem;'>✅ {chunk_count} chunks | {len(doc_list)} doc(s)</span></div>",
                    unsafe_allow_html=True
                )
                for doc in doc_list:
                    col_d, col_del = st.columns([4, 1])
                    with col_d:
                        st.markdown(f"<span style='font-size:0.8rem; color:#334155;'>📄 {doc[:30]}</span>", unsafe_allow_html=True)
                    with col_del:
                        if st.button("🗑️", key=f"del_{doc}", help=f"Remove {doc}"):
                            delete_from_library(doc)
                            st.rerun()
                st.write("")
            uploaded_pdf = st.file_uploader(
                "Upload PDF", type=["pdf"],
                help="Upload academic papers, thesis notes, or previous research reports.",
                key="library_pdf_uploader"
            )
            if uploaded_pdf is not None:
                if st.button("📥 Index this PDF", key="index_pdf_btn", use_container_width=True):
                    with st.spinner(f"Indexing '{uploaded_pdf.name}'..."):
                        result_lib = index_user_pdf(uploaded_pdf.read(), uploaded_pdf.name)
                        if result_lib["success"]:
                            st.success(f"✅ Indexed {result_lib['chunks_indexed']} chunks!")
                            st.rerun()
                        else:
                            st.error(f"❌ {result_lib['message']}")
        except ImportError:
            st.info("📦 Install pdfplumber: `pip install pdfplumber`")
        except Exception as e:
            st.warning(f"Library unavailable: {e}")

# ── Store sidebar config in session ──────────────────────────────────────────
if sidebar_tab != "📜 History" and sidebar_tab != "🕵️ Agents":
    st.session_state["llm_type"]     = llm_type
    st.session_state["model_name"]   = model_name
    st.session_state["hitl_enabled"] = hitl_enabled
    st.session_state["compare_mode"] = compare_mode

# Pull config from session (safe defaults)
llm_type     = st.session_state.get("llm_type", "groq")
model_name   = st.session_state.get("model_name", None)
hitl_enabled = st.session_state.get("hitl_enabled", True)
compare_mode = st.session_state.get("compare_mode", False)


# ══════════════════════════════════════════════════════════════════════════════
# TOPIC INPUT AREA
# ══════════════════════════════════════════════════════════════════════════════

if not compare_mode:
    # ── Single Topic Mode ─────────────────────────────────────────────────────

    # Trending topic suggestions
    domains = get_all_domains()
    st.markdown("**💡 Trending Research Domains:**", unsafe_allow_html=True)
    domain_pills = "".join([
        f"<span class='tag-pill' id='domain_{i}'>{d}</span>"
        for i, d in enumerate(domains)
    ])
    st.markdown(domain_pills, unsafe_allow_html=True)

    col_topic, col_random, col_btn = st.columns([5, 1.2, 1])

    with col_topic:
        topic = st.text_input(
            "Research Topic",
            placeholder="e.g. Federated Learning for Privacy-Preserving AI",
            help="Be specific for best results.",
            key="topic_input"
        )

    with col_random:
        st.write("")
        st.write("")
        if st.button("🎲 Random", use_container_width=True, help="Pick a random trending topic"):
            st.session_state["random_topic"] = get_random_topic()
            st.rerun()

    with col_btn:
        st.write("")
        st.write("")
        generate_btn = st.button("🚀 Generate", use_container_width=True)

    # Apply random topic
    if st.session_state.get("random_topic"):
        topic = st.session_state.pop("random_topic")

    # Topic suggestions
    if topic and len(topic) >= 3:
        suggestions = get_suggestions(topic, max_results=4)
        if suggestions:
            st.markdown("**🔍 Suggestions:**")
            sug_cols = st.columns(len(suggestions))
            for i, sug in enumerate(suggestions):
                with sug_cols[i]:
                    if st.button(f"📌 {sug[:45]}...", key=f"sug_{i}", use_container_width=True):
                        st.session_state["random_topic"] = sug
                        st.rerun()

    # Curated topics by domain
    with st.expander("📂 Browse Topics by Domain"):
        sel_domain = st.selectbox("Domain", domains, key="domain_sel")
        domain_topics = TRENDING_TOPICS.get(sel_domain, [])
        for t in domain_topics:
            if st.button(f"  → {t}", key=f"dt_{t[:20]}", use_container_width=False):
                st.session_state["random_topic"] = t
                st.rerun()

else:
    # ── Compare Mode ──────────────────────────────────────────────────────────
    st.markdown(
        "<div style='background:rgba(59,130,246,0.05); border:1px solid rgba(59,130,246,0.15); "
        "border-radius:12px; padding:14px 18px; margin-bottom:16px;'>"
        "<b style='color:#3b82f6;'>⚖️ Multi-Topic Comparison Mode</b> &nbsp;— "
        "<span style='color:#334155; font-size:0.9rem;'>Research two topics simultaneously and compare results side-by-side</span>"
        "</div>",
        unsafe_allow_html=True
    )
    col_a, col_b = st.columns(2)
    with col_a:
        topic_a = st.text_input("🔵 Topic A", placeholder="e.g. Quantum Computing Applications",
                                key="topic_a_input")
    with col_b:
        topic_b = st.text_input("🟣 Topic B", placeholder="e.g. Classical Computing Limitations",
                                key="topic_b_input")
    topic = topic_a  # For HITL compatibility
    generate_btn = st.button("🚀 Compare Both Topics", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# HITL REVIEW PANEL
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.hitl_pending and st.session_state.partial_state:
    partial  = st.session_state.partial_state
    verified = partial.get("verified_claims", [])

    st.markdown("<div class='hitl-card'>", unsafe_allow_html=True)
    st.markdown("## ⏸️ Human Review Required — Fact Checker Complete")
    st.markdown(
        f"**{len(verified)} verified claims** extracted. "
        "Review below, add optional guidance, then approve."
    )

    with st.expander(f"📋 View {len(verified)} Verified Claims", expanded=True):
        # Group by confidence
        high_conf = [c for c in verified if c.get("confidence", 0) >= 80]
        med_conf  = [c for c in verified if 60 <= c.get("confidence", 0) < 80]
        low_conf  = [c for c in verified if c.get("confidence", 0) < 60]

        if high_conf:
            st.markdown("**✅ High Confidence (≥80%)**")
            for i, c in enumerate(high_conf, 1):
                st.markdown(
                    f"**{i}.** {c['claim']} "
                    f"<span class='cred-badge-high'>{c.get('confidence','?')}%</span>",
                    unsafe_allow_html=True
                )
        if med_conf:
            st.markdown("**⚠️ Medium Confidence (60–79%)**")
            for i, c in enumerate(med_conf, 1):
                st.markdown(
                    f"**{i}.** {c['claim']} "
                    f"<span class='cred-badge-medium'>{c.get('confidence','?')}%</span>",
                    unsafe_allow_html=True
                )
        if low_conf:
            st.markdown("**❌ Lower Confidence (<60%)**")
            for i, c in enumerate(low_conf, 1):
                st.markdown(
                    f"**{i}.** {c['claim']} "
                    f"<span class='cred-badge-low'>{c.get('confidence','?')}%</span>",
                    unsafe_allow_html=True
                )

    human_note = st.text_area(
        "📝 Optional guidance for the Writer agent",
        placeholder="e.g. 'Focus more on economic implications' or 'Include more recent 2025 data'",
        height=80
    )

    col_approve, col_reject = st.columns(2)
    with col_approve:
        if st.button("✅ Approve & Continue to Writer", use_container_width=True):
            st.session_state.partial_state["human_approved"] = True
            st.session_state.partial_state["hitl_feedback"]  = human_note
            st.session_state.hitl_pending = False
            st.rerun()
    with col_reject:
        if st.button("🔄 Reject — Re-run Researcher", use_container_width=True):
            st.session_state.partial_state["human_approved"] = False
            st.session_state.partial_state["cached_from_db"] = False
            st.session_state.partial_state["raw_sources"]    = []
            st.session_state.partial_state["verified_claims"] = []
            st.session_state.hitl_pending = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ══════════════════════════════════════════════════════════════════════════════
def run_pipeline(topic: str, llm_type: str, model_name, human_approved: bool) -> dict | None:
    """Runs the full multi-agent pipeline with live streaming UI updates."""

    status_panel = st.empty()
    log_panel    = st.empty()

    with status_panel.container():
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(
            f"<h3 style='color:#0f172a; margin-bottom:12px;'>⛓️ Running Research Pipeline"
            f"<span style='color:#475569; font-size:0.85rem; font-weight:400;'> — {llm_type.upper()}</span></h3>",
            unsafe_allow_html=True
        )
        progress_bar = st.progress(3)

        cols = st.columns(7)
        labels = ["Cache", "Researcher", "Fact Checker", "HITL", "Analyst", "Writer", "Critic"]
        widgets = [c.empty() for c in cols]
        for w, label in zip(widgets, labels):
            w.markdown(f"<div style='text-align:center; font-size:0.78rem; color:#475569;'>⏳ {label}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with log_panel.container():
        st.markdown("### 📡 Live Agent Stream")
        log_box = st.empty()

    events_log = []

    def _mark(widget, label, status):
        colors_map = {"done": "#0f766e", "running": "#3b82f6", "skip": "#3b82f6"}
        icons_map  = {"done": "✅", "running": "⚡", "skip": "⚡"}
        color = colors_map.get(status, "#94a3b8")
        icon  = icons_map.get(status, "⏳")
        widget.markdown(
            f"<div style='text-align:center; font-size:0.78rem; color:{color}; font-weight:600;'>{icon} {label}</div>",
            unsafe_allow_html=True
        )

    def refresh_log():
        html = "".join([f"<div class='activity-node'>{m}</div>" for m in events_log[-12:]])
        log_box.markdown(html, unsafe_allow_html=True)

    try:
        graph  = get_cached_graph()
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        inputs = make_initial_state(
            topic=topic, llm_type=llm_type, llm_name=model_name,
            human_approved=human_approved, thread_id=st.session_state.thread_id
        )

        w = widgets
        result = None

        for event in graph.stream(inputs, config=config):
            for node_name, output in event.items():

                if node_name == "__interrupt__":
                    _mark(w[3], "HITL", "running")
                    events_log.append("⏸️ <b>HITL checkpoint</b> — pipeline paused for human review.")
                    refresh_log()
                    status_panel.empty(); log_panel.empty()
                    st.session_state.hitl_pending  = True
                    st.session_state.partial_state = dict(inputs)
                    current = graph.get_state(config)
                    if current and current.values:
                        st.session_state.partial_state = dict(current.values)
                    st.rerun()
                    return

                elif node_name == "cache_check":
                    hit = output.get("cached_from_db", False)
                    _mark(w[0], "Cache", "done")
                    _mark(w[1], "Researcher", "skip" if hit else "running")
                    progress_bar.progress(12)
                    cache_msg = "<b style='color:#10b981;'>Cache HIT!</b> Skipping live search." if hit else "Cache MISS. Running live search."
                    events_log.append(f"🗄️ <b>Cache Check</b> — {cache_msg}")

                elif node_name == "researcher":
                    src = output.get("raw_sources", [])
                    src_by_type = {}
                    for s in src:
                        t = s.get("source_type", "web")
                        src_by_type[t] = src_by_type.get(t, 0) + 1
                    breakdown = " | ".join([f"{v} {k}" for k, v in src_by_type.items()])
                    _mark(w[1], "Researcher", "done")
                    _mark(w[2], "Fact Checker", "running")
                    progress_bar.progress(30)
                    events_log.append(
                        f"🔍 <b>Researcher</b> — Harvested <b>{len(src)}</b> sources ({breakdown})"
                    )

                elif node_name == "fact_checker":
                    claims = output.get("verified_claims", [])
                    _mark(w[2], "Fact Checker", "done")
                    _mark(w[3], "HITL", "running" if hitl_enabled else "skip")
                    progress_bar.progress(50)
                    avg_conf = sum(c.get("confidence", 0) for c in claims) // max(len(claims), 1)
                    events_log.append(
                        f"🛡️ <b>Fact Checker</b> — <b>{len(claims)}</b> VERIFIED claims "
                        f"(avg confidence: <b>{avg_conf}%</b>)"
                    )

                elif node_name == "human_review":
                    _mark(w[3], "HITL", "done")
                    _mark(w[4], "Analyst", "running")
                    progress_bar.progress(60)
                    events_log.append("✅ <b>Human review</b> approved. Proceeding to Analyst.")

                elif node_name == "analyst":
                    _mark(w[4], "Analyst", "done")
                    _mark(w[5], "Writer", "running")
                    progress_bar.progress(72)
                    t = output.get("agent_timings", {}).get("analyst", 0)
                    events_log.append(
                        f"📊 <b>Analyst</b> — Extracted statistics, trends & implications "
                        f"({t:.1f}s)"
                    )

                elif node_name == "writer":
                    words = output.get("word_count", 0)
                    iters = output.get("iterations", 1)
                    _mark(w[5], "Writer", "done")
                    _mark(w[6], "Critic", "running")
                    progress_bar.progress(85)
                    t = output.get("agent_timings", {}).get(f"writer_{iters}", 0)
                    events_log.append(
                        f"✍️ <b>Writer</b> — Draft #{iters} complete "
                        f"(<b>{words:,} words</b>, {t:.1f}s)"
                    )

                elif node_name == "critic":
                    score = output.get("quality_score", 0)
                    iters = output.get("iterations", 0)
                    t = output.get("agent_timings", {}).get("critic", 0)
                    if score < 70 and iters < 3:
                        _mark(w[5], "Writer", "running")
                        _mark(w[6], "Critic", "skip")
                        events_log.append(
                            f"⚠️ <b>Critic rejected</b> (Score: <b>{score}/100</b>) — "
                            f"Requesting rewrite #{iters + 1} ({t:.1f}s)"
                        )
                    else:
                        _mark(w[6], "Critic", "done")
                        progress_bar.progress(95)
                        grade = "EXCELLENT ⭐" if score >= 85 else "GOOD ✓" if score >= 70 else "PASS"
                        events_log.append(
                            f"🧐 <b>Critic APPROVED</b> — Score: <b>{score}/100</b> ({grade}) in {t:.1f}s"
                        )

                elif node_name == "pdf_gen":
                    progress_bar.progress(100)
                    events_log.append("📄 <b>PDF + History</b> — Report saved successfully!")
                    result = output

                refresh_log()
                time.sleep(0.3)

        if result is None:
            final = graph.get_state(config)
            result = dict(final.values) if final and final.values else {}

        status_panel.empty()
        log_panel.empty()
        st.session_state.result = result
        return result

    except Exception as e:
        status_panel.empty()
        log_panel.empty()
        st.error(f"❌ Workflow Error: {e}")
        import traceback
        with st.expander("🔍 Full Error Traceback"):
            st.code(traceback.format_exc())
        st.info(
            "**Troubleshooting:**\n"
            "- Groq: Check `GROQ_API_KEY` in `.env`\n"
            "- Gemini: Check `GOOGLE_API_KEY` in `.env`\n"
            "- Ollama: Run `ollama serve` and ensure model is pulled"
        )
        return None


# ══════════════════════════════════════════════════════════════════════════════
# TRIGGER PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
if generate_btn:
    if compare_mode:
        ta = st.session_state.get("topic_a_input", "")
        tb = st.session_state.get("topic_b_input", "")
        if not ta or not tb:
            st.warning("⚠️ Please enter both Topic A and Topic B for comparison.")
        else:
            st.session_state.result           = None
            st.session_state.compare_result_a = None
            st.session_state.compare_result_b = None

            st.markdown("### 🔵 Researching Topic A...")
            ra = run_pipeline(ta, llm_type, model_name, not hitl_enabled)
            st.session_state.compare_result_a = ra
            st.session_state.topic_a = ta

            st.markdown("### 🟣 Researching Topic B...")
            rb = run_pipeline(tb, llm_type, model_name, not hitl_enabled)
            st.session_state.compare_result_b = rb
            st.session_state.topic_b = tb
    else:
        if not topic:
            st.warning("⚠️ Please enter a research topic.")
        else:
            st.session_state.hitl_pending  = False
            st.session_state.partial_state = None
            st.session_state.result        = None
            human_approved = not hitl_enabled
            result = run_pipeline(topic, llm_type, model_name, human_approved)
            if result:
                st.session_state.result = result


# ── Resume After HITL Approval ────────────────────────────────────────────────
if (not st.session_state.hitl_pending
        and st.session_state.partial_state is not None
        and st.session_state.result is None):

    approved_state = st.session_state.partial_state
    if approved_state.get("human_approved"):
        st.info("▶️ Resuming pipeline from HITL checkpoint...")
        st.session_state.partial_state = None

        try:
            from langgraph.types import Command
            graph  = get_cached_graph()
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            resume_result = graph.invoke(
                Command(resume={"decision": "APPROVE", "note": approved_state.get("hitl_feedback", "")}),
                config=config
            )
            st.session_state.result = resume_result
        except Exception as e:
            st.error(f"❌ Resume error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY RESULTS
# ══════════════════════════════════════════════════════════════════════════════
def _render_result(result: dict, topic: str = ""):
    """Render a single research result with all panels."""

    if not result:
        return

    if result.get("error"):
        st.error(f"❌ Pipeline error: {result['error']}")

    st.success("🎉 Research completed successfully!")

    # ── Main Report Tabs ──────────────────────────────────────────────────────
    tab_report, tab_analytics, tab_sources, tab_gaps, tab_citation = st.tabs(
        ["📄 Report", "📊 Analytics", "🔍 Sources & Claims", "🔬 Research Gaps", "🕸️ Citation Graph"]
    )

    # ── TAB 1: REPORT ─────────────────────────────────────────────────────────
    with tab_report:
        col_report, col_meta = st.columns([7, 3])

        with col_report:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)

            # Cache badge
            if result.get("cached_from_db"):
                st.markdown(
                    "<span style='background:rgba(16,185,129,0.12); color:#10b981; "
                    "padding:4px 12px; border-radius:20px; font-size:0.8rem; "
                    "border:1px solid rgba(16,185,129,0.2);'>⚡ Loaded from ChromaDB Cache</span>",
                    unsafe_allow_html=True
                )
                st.write("")

            # Typewriter animation for report
            report_text = result.get("report_draft", "_No report generated._")
            report_placeholder = st.empty()

            def _stream_report():
                words = report_text.split(" ")
                buf = ""
                for i, w in enumerate(words):
                    buf += w + " "
                    if i % 15 == 0:  # Update every 15 words for performance
                        yield buf
                yield report_text  # Final full text

            if st.session_state.get("report_streamed_" + result.get("thread_id", ""), False):
                report_placeholder.markdown(report_text)
            else:
                displayed = ""
                for chunk in _stream_report():
                    displayed = chunk
                    report_placeholder.markdown(chunk)
                    time.sleep(0.04)
                st.session_state["report_streamed_" + result.get("thread_id", "")] = True

            st.markdown("</div>", unsafe_allow_html=True)

            # ── EXPORT BUTTONS ────────────────────────────────────────────────
            st.markdown("#### 📥 Export Report")
            ecol1, ecol2, ecol3 = st.columns(3)

            with ecol1:
                # PDF download
                pdf_path = result.get("pdf_path", "")
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📕 Download PDF",
                            data=f.read(),
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            use_container_width=True,
                        )
                else:
                    st.warning("PDF not available.")

            with ecol2:
                # Markdown download
                clean_t = "".join(c for c in (topic or result.get("topic", "research"))[:30]
                                  if c.isalnum() or c in (' ', '_')).replace(' ', '_')
                md_filename = f"research_{clean_t}.md"
                st.download_button(
                    label="📝 Download Markdown",
                    data=report_text.encode("utf-8"),
                    file_name=md_filename,
                    mime="text/markdown",
                    use_container_width=True,
                )

            with ecol3:
                # Word export
                try:
                    from tools.word_exporter import generate_word
                    word_path = generate_word(
                        topic=topic or result.get("topic", "Research"),
                        report=report_text,
                        quality_score=result.get("quality_score", 0),
                        verified_count=len(result.get("verified_claims", [])),
                        llm_type=result.get("llm_type", "groq"),
                    )
                    if word_path and os.path.exists(word_path):
                        with open(word_path, "rb") as f:
                            st.download_button(
                                label="📘 Download Word",
                                data=f.read(),
                                file_name=os.path.basename(word_path),
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True,
                            )
                except Exception as e:
                    st.warning(f"Word export unavailable: {e}")

            # ── ACADEMIC FORMAT EXPORTS (Phase 1 Feature 7) ───────────────────
            st.markdown("##### 🎓 Academic & Presentation Formats")
            try:
                from tools.export_formats import (
                    export_apa_literature_review,
                    export_ieee_format,
                    export_slide_outline,
                    export_obsidian_markdown,
                )
                _r_topic    = topic or result.get("topic", "Research")
                _r_claims   = result.get("verified_claims", [])
                _r_insights = result.get("insights", [])
                _r_gaps     = result.get("research_gaps", [])

                acol1, acol2, acol3, acol4 = st.columns(4)
                with acol1:
                    apa_text = export_apa_literature_review(report_text, _r_claims, _r_topic, _r_gaps)
                    st.download_button(
                        label="📚 APA Review",
                        data=apa_text.encode("utf-8"),
                        file_name=f"apa_{_r_topic[:20].replace(' ','_')}.md",
                        mime="text/markdown",
                        use_container_width=True,
                        help="APA 7th Edition formatted literature review"
                    )
                with acol2:
                    ieee_text = export_ieee_format(report_text, _r_claims, _r_topic, _r_gaps)
                    st.download_button(
                        label="⚙️ IEEE Format",
                        data=ieee_text.encode("utf-8"),
                        file_name=f"ieee_{_r_topic[:20].replace(' ','_')}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        help="IEEE technical paper format with numbered references"
                    )
                with acol3:
                    slide_text = export_slide_outline(_r_insights, _r_claims, _r_topic, _r_gaps)
                    st.download_button(
                        label="📊 Slide Outline",
                        data=slide_text.encode("utf-8"),
                        file_name=f"slides_{_r_topic[:20].replace(' ','_')}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        help="6-slide presentation outline for PowerPoint / Google Slides"
                    )
                with acol4:
                    obsidian_text = export_obsidian_markdown(report_text, _r_claims, _r_topic, _r_gaps)
                    st.download_button(
                        label="🗂️ Obsidian MD",
                        data=obsidian_text.encode("utf-8"),
                        file_name=f"obsidian_{_r_topic[:20].replace(' ','_')}.md",
                        mime="text/markdown",
                        use_container_width=True,
                        help="Obsidian-compatible Markdown with YAML frontmatter and wikilinks"
                    )
            except Exception as e:
                st.info(f"Academic export formats loading... ({e})")

        with col_meta:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("### 📊 Report Metrics")

            score = result.get("quality_score", 0)
            s_color = "#10b981" if score >= 80 else "#f59e0b" if score >= 70 else "#ef4444"
            s_bg    = "rgba(16,185,129,0.1)" if score >= 80 else "rgba(245,158,11,0.1)" if score >= 70 else "rgba(239,68,68,0.1)"
            st.markdown(
                f"<div style='text-align:center; background:{s_bg}; border-radius:12px; "
                f"padding:16px 8px; margin-bottom:16px;'>"
                f"<div style='font-size:3rem; font-weight:800; color:{s_color};'>{score}</div>"
                f"<div style='color:#475569; font-size:0.8rem;'>/ 100 &nbsp; Quality Score</div>"
                f"</div>",
                unsafe_allow_html=True
            )

            st.metric("Verified Claims",  len(result.get("verified_claims", [])))
            st.metric("Word Count",       f"~{result.get('word_count', 0):,}")
            st.metric("Revision Loops",   result.get("iterations", 0))
            st.metric("Sources Fetched",  len(result.get("raw_sources", [])))
            st.metric("Cache Used",       "✅ Yes" if result.get("cached_from_db") else "❌ No")

            if result.get("critic_feedback"):
                st.markdown("##### 🧐 Critic Notes")
                st.info(result["critic_feedback"][:500])

            st.markdown("</div>", unsafe_allow_html=True)

    # ── TAB 2: ANALYTICS ──────────────────────────────────────────────────────
    with tab_analytics:
        import plotly.graph_objects as go
        import plotly.express as px

        st.markdown("### 📊 Pipeline Performance Analytics")

        timings = result.get("agent_timings") or {}
        verified = result.get("verified_claims", [])
        raw_sources = result.get("raw_sources", [])

        analytics_col1, analytics_col2 = st.columns(2)

        # Chart 1: Agent Timing Bar Chart
        with analytics_col1:
            if timings:
                agent_labels = list(timings.keys())
                agent_times  = list(timings.values())
                colors_list  = ["#0f172a", "#3b82f6", "#0f766e", "#10b981", "#fb923c", "#f59e0b", "#64748b"]

                fig_timing = go.Figure(go.Bar(
                    x=agent_labels,
                    y=agent_times,
                    marker_color=colors_list[:len(agent_labels)],
                    text=[f"{t:.1f}s" for t in agent_times],
                    textposition="outside",
                ))
                fig_timing.update_layout(
                    title="⏱️ Agent Execution Time (seconds)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#475569", size=11),
                    title_font=dict(color="#0f172a", size=13),
                    showlegend=False,
                    yaxis=dict(gridcolor="rgba(15,23,42,0.08)", title="Seconds"),
                    xaxis=dict(title=""),
                    height=320,
                    margin=dict(t=50, b=30, l=20, r=20),
                )
                st.plotly_chart(fig_timing, use_container_width=True)
            else:
                st.info("No timing data available yet.")

        # Chart 2: Source Type Distribution Pie
        with analytics_col2:
            if raw_sources:
                type_counts = {}
                for s in raw_sources:
                    t = s.get("source_type", "web")
                    type_counts[t] = type_counts.get(t, 0) + 1

                type_colors = {
                    "arxiv": "#3b82f6", "wikipedia": "#10b981",
                    "web": "#64748b", "news": "#fb923c",
                    "pubmed": "#ec4899", "openalex": "#8b5cf6"
                }
                labels = list(type_counts.keys())
                values = list(type_counts.values())
                pie_colors = [type_colors.get(l, "#64748b") for l in labels]

                fig_pie = go.Figure(go.Pie(
                    labels=labels,
                    values=values,
                    marker_colors=pie_colors,
                    hole=0.4,
                    textinfo="label+percent",
                    textfont=dict(color="#ffffff"),
                ))
                fig_pie.update_layout(
                    title="🗂️ Source Type Distribution",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#475569", size=11),
                    title_font=dict(color="#0f172a", size=13),
                    showlegend=True,
                    legend=dict(font=dict(color="#475569")),
                    height=320,
                    margin=dict(t=50, b=20, l=20, r=20),
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        analytics_col3, analytics_col4 = st.columns(2)

        # Chart 3: Confidence Score Histogram
        with analytics_col3:
            if verified:
                confs = [c.get("confidence", 0) for c in verified]
                fig_hist = go.Figure(go.Histogram(
                    x=confs,
                    nbinsx=10,
                    marker_color="#3b82f6",
                    marker_line=dict(color="#0f172a", width=1),
                    opacity=0.8,
                ))
                fig_hist.update_layout(
                    title="📈 Confidence Score Distribution",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#475569", size=11),
                    title_font=dict(color="#0f172a", size=13),
                    xaxis=dict(title="Confidence %", gridcolor="rgba(15,23,42,0.08)", range=[0, 100]),
                    yaxis=dict(title="Claims", gridcolor="rgba(15,23,42,0.08)"),
                    height=300,
                    margin=dict(t=50, b=30, l=20, r=20),
                )
                st.plotly_chart(fig_hist, use_container_width=True)

        # Chart 4: Source Credibility Bar
        with analytics_col4:
            if raw_sources and any("credibility_score" in s for s in raw_sources):
                cred_by_type = {}
                count_by_type = {}
                for s in raw_sources:
                    t   = s.get("source_type", "web")
                    cr  = s.get("credibility_score", 60)
                    cred_by_type[t]  = cred_by_type.get(t, 0) + cr
                    count_by_type[t] = count_by_type.get(t, 0) + 1
                avg_cred = {t: round(cred_by_type[t] / count_by_type[t]) for t in cred_by_type}

                type_colors = {
                    "arxiv": "#3b82f6", "wikipedia": "#10b981",
                    "web": "#64748b", "news": "#fb923c",
                    "pubmed": "#ec4899", "openalex": "#8b5cf6"
                }
                fig_cred = go.Figure(go.Bar(
                    x=list(avg_cred.keys()),
                    y=list(avg_cred.values()),
                    marker_color=[type_colors.get(t, "#64748b") for t in avg_cred.keys()],
                    text=[f"{v}/100" for v in avg_cred.values()],
                    textposition="outside",
                ))
                fig_cred.add_hline(y=80, line_dash="dot", line_color="rgba(16,185,129,0.4)",
                                   annotation_text="High credibility threshold", annotation_font_color="#10b981")
                fig_cred.update_layout(
                    title="🏅 Avg Source Credibility by Type",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#475569", size=11),
                    title_font=dict(color="#0f172a", size=13),
                    yaxis=dict(title="Credibility Score", range=[0, 105], gridcolor="rgba(15,23,42,0.08)"),
                    height=300,
                    margin=dict(t=50, b=30, l=20, r=20),
                )
                st.plotly_chart(fig_cred, use_container_width=True)

        # Summary metrics row
        st.divider()
        m1, m2, m3, m4, m5 = st.columns(5)
        total_time = sum(timings.values()) if timings else 0
        m1.metric("Total Pipeline Time", f"{total_time:.0f}s")
        m2.metric("Sources Analyzed",    len(raw_sources))
        m3.metric("Claims Verified",     len(verified))
        m4.metric("Avg Confidence",
                  f"{sum(c.get('confidence',0) for c in verified)//max(len(verified),1)}%")
        m5.metric("Report Words",        f"{result.get('word_count', 0):,}")

    # ── TAB 3: SOURCES ────────────────────────────────────────────────────────
    with tab_sources:
        st.markdown("### 🔍 Verified Claims with Confidence Scores")

        if verified:
            for i, claim in enumerate(result.get("verified_claims", []), 1):
                conf  = claim.get("confidence", 0)
                badge_cls = "cred-badge-high" if conf >= 80 else "cred-badge-medium" if conf >= 60 else "cred-badge-low"
                st.markdown(
                    f"**{i}.** {claim['claim']} "
                    f"<span class='{badge_cls}'>{conf}%</span>",
                    unsafe_allow_html=True
                )
        else:
            st.info("No verified claims in this result.")

        st.divider()
        st.markdown("### 📚 Raw Sources with Credibility Scores")

        if raw_sources:
            # Group by source type
            by_type = {}
            for s in raw_sources:
                t = s.get("source_type", "web")
                by_type.setdefault(t, []).append(s)

            for src_type, sources in sorted(by_type.items(), key=lambda x: -len(x[1])):
                type_icons = {"arxiv": "📑", "wikipedia": "📖", "web": "🌐", "news": "📰", "pubmed": "🧬", "openalex": "🎓"}
                icon = type_icons.get(src_type, "🔗")
                st.markdown(f"#### {icon} {src_type.upper()} ({len(sources)} sources)")
                for s in sources:
                    cred = s.get("credibility_score", 60)
                    badge_cls = "cred-badge-high" if cred >= 80 else "cred-badge-medium" if cred >= 65 else "cred-badge-low"
                    with st.expander(f"{s.get('title', 'Source')[:80]}"):
                        col_s1, col_s2 = st.columns([4, 1])
                        with col_s1:
                            st.markdown(f"**URL:** `{s.get('url', 'N/A')}`")
                            st.markdown(f"**Preview:** {s.get('content', '')[:400]}...")
                        with col_s2:
                            st.markdown(
                                f"<div style='text-align:center; padding-top:8px;'>"
                                f"<span class='{badge_cls}'>Credibility<br>{cred}/100</span></div>",
                                unsafe_allow_html=True
                            )
        else:
            st.info("No raw sources available.")

    # ── TAB 4: RESEARCH GAPS ──────────────────────────────────────────────────
    with tab_gaps:
        st.markdown("### 🔬 Research Gap Analysis")
        st.markdown(
            "<div style='background:rgba(245,158,11,0.07); border:1px solid rgba(245,158,11,0.2); "
            "border-radius:12px; padding:14px 18px; margin-bottom:20px;'>"
            "<b style='color:#d97706;'>🧠 What is Research Gap Analysis?</b><br>"
            "<span style='color:#78350f; font-size:0.92rem;'>"
            "This section identifies what the current research does <b>NOT</b> answer. "
            "These are the open questions, methodological limitations, contradictions, and future directions "
            "that researchers, PhD students, and R&D teams should investigate next. "
            "Unlike generic summaries, this gap analysis was produced by a dedicated AI reasoning agent "
            "that specifically analyzed the verified claims to find knowledge frontiers."
            "</span></div>",
            unsafe_allow_html=True
        )

        research_gaps = result.get("research_gaps", [])
        if research_gaps:
            # Group by gap type
            type_config = {
                "[OPEN QUESTION]": {"icon": "❓", "color": "#3b82f6", "bg": "rgba(59,130,246,0.07)", "border": "rgba(59,130,246,0.25)"},
                "[LIMITATION]":    {"icon": "⚠️", "color": "#f59e0b", "bg": "rgba(245,158,11,0.07)", "border": "rgba(245,158,11,0.25)"},
                "[FUTURE DIRECTION]": {"icon": "🚀", "color": "#10b981", "bg": "rgba(16,185,129,0.07)", "border": "rgba(16,185,129,0.25)"},
                "[CONTRADICTION]": {"icon": "⚡", "color": "#ef4444", "bg": "rgba(239,68,68,0.07)", "border": "rgba(239,68,68,0.25)"},
                "[MISSING DATA]": {"icon": "🔍", "color": "#8b5cf6", "bg": "rgba(139,92,246,0.07)", "border": "rgba(139,92,246,0.25)"},
            }
            default_cfg = {"icon": "📌", "color": "#64748b", "bg": "rgba(100,116,139,0.07)", "border": "rgba(100,116,139,0.25)"}

            st.metric("Total Gaps Identified", len(research_gaps))
            st.write("")

            for i, gap in enumerate(research_gaps, 1):
                # Identify gap type from prefix
                cfg = default_cfg
                display_gap = gap
                for tag, c in type_config.items():
                    if gap.startswith(tag):
                        cfg = c
                        display_gap = gap[len(tag):].strip()
                        break

                st.markdown(
                    f"<div style='background:{cfg['bg']}; border:1px solid {cfg['border']}; "
                    f"border-radius:10px; padding:12px 16px; margin-bottom:10px;'>"
                    f"<span style='color:{cfg['color']}; font-weight:700; font-size:0.85rem;'>{cfg['icon']} GAP #{i}</span><br>"
                    f"<span style='color:#0f172a; font-size:0.95rem;'>{display_gap}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Research gap analysis not yet run or no gaps identified for this topic.")

    # ── TAB 5: CITATION GRAPH ─────────────────────────────────────────────────
    with tab_citation:
        st.markdown("### 🕸️ Citation Landscape")
        st.markdown(
            "<div style='background:rgba(59,130,246,0.07); border:1px solid rgba(59,130,246,0.2); "
            "border-radius:12px; padding:14px 18px; margin-bottom:20px;'>"
            "<b style='color:#1d4ed8;'>📡 How Citation Graphs Work</b><br>"
            "<span style='color:#1e3a5f; font-size:0.92rem;'>"
            "The Citation Landscape maps the intellectual lineage of papers found during this research. "
            "Blue nodes = the source papers. Green nodes = papers that cite this work (follow-on research). "
            "Orange nodes = papers cited by this work (foundational prior art). "
            "This gives you a full map of the knowledge network, not just a single paper summary."
            "</span></div>",
            unsafe_allow_html=True
        )

        arxiv_sources = [s for s in result.get("raw_sources", []) if s.get("source_type") == "arxiv"]
        if arxiv_sources:
            st.markdown(f"**Found {len(arxiv_sources)} ArXiv papers in this research run.**")
            paper_options = {s.get("title", f"Paper {i+1}"): s.get("url", "") for i, s in enumerate(arxiv_sources[:5])}
            selected_paper = st.selectbox("Select a paper to visualize its citation network:", list(paper_options.keys()))
            selected_url = paper_options.get(selected_paper, "")

            if st.button("🔍 Load Citation Graph", key="load_citation_graph"):
                with st.spinner("Fetching citation data from Semantic Scholar..."):
                    try:
                        from tools.citation_graph import fetch_and_render_citation_graph
                        graph_html = fetch_and_render_citation_graph(selected_url, selected_paper)
                        if graph_html:
                            import streamlit.components.v1 as components
                            components.html(graph_html, height=600, scrolling=True)
                        else:
                            st.warning("No citation data found for this paper. Try another paper.")
                    except ImportError:
                        st.info("📦 Citation Graph requires additional packages. Run: pip install networkx pyvis requests")
                    except Exception as e:
                        st.error(f"Citation graph error: {e}")
        else:
            st.info("No ArXiv papers were found in this research run. ArXiv papers are required for citation graphs. Try a more technical/scientific topic.")


# ── RENDER SINGLE RESULT ──────────────────────────────────────────────────────
if st.session_state.result and not compare_mode:
    _render_result(st.session_state.result, topic=st.session_state.get("topic_input", ""))

# ── RENDER COMPARISON RESULTS ─────────────────────────────────────────────────
if compare_mode and (st.session_state.compare_result_a or st.session_state.compare_result_b):
    st.divider()
    st.markdown("## ⚖️ Side-by-Side Research Comparison")

    ra = st.session_state.compare_result_a
    rb = st.session_state.compare_result_b
    ta = st.session_state.get("topic_a", "Topic A")
    tb = st.session_state.get("topic_b", "Topic B")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(
            f"<div style='background:rgba(59,130,246,0.05); border:1px solid rgba(59,130,246,0.15); "
            f"border-radius:12px; padding:12px 16px; margin-bottom:12px;'>"
            f"<b style='color:#3b82f6;'>🔵 {ta[:60]}</b></div>",
            unsafe_allow_html=True
        )
        if ra:
            score_a = ra.get("quality_score", 0)
            s_c = "#10b981" if score_a >= 80 else "#f59e0b" if score_a >= 70 else "#ef4444"
            st.metric("Quality Score", f"{score_a}/100")
            st.metric("Verified Claims", len(ra.get("verified_claims", [])))
            st.metric("Words", f"{ra.get('word_count', 0):,}")
            with st.expander("📄 View Report A"):
                st.markdown(ra.get("report_draft", "No report."))
            # Download
            md_a = ra.get("report_draft", "")
            st.download_button("📝 Download Report A (MD)", md_a.encode(),
                               file_name="report_a.md", mime="text/markdown",
                               use_container_width=True)

    with col_b:
        st.markdown(
            f"<div style='background:rgba(15,118,110,0.05); border:1px solid rgba(15,118,110,0.15); "
            f"border-radius:12px; padding:12px 16px; margin-bottom:12px;'>"
            f"<b style='color:#0f766e;'>🟣 {tb[:60]}</b></div>",
            unsafe_allow_html=True
        )
        if rb:
            score_b = rb.get("quality_score", 0)
            st.metric("Quality Score", f"{score_b}/100")
            st.metric("Verified Claims", len(rb.get("verified_claims", [])))
            st.metric("Words", f"{rb.get('word_count', 0):,}")
            with st.expander("📄 View Report B"):
                st.markdown(rb.get("report_draft", "No report."))
            md_b = rb.get("report_draft", "")
            st.download_button("📝 Download Report B (MD)", md_b.encode(),
                               file_name="report_b.md", mime="text/markdown",
                               use_container_width=True)

    # Comparison summary bar chart
    if ra and rb:
        import plotly.graph_objects as go
        metrics = ["Quality Score", "Verified Claims", "Word Count (×10)"]
        vals_a  = [
            ra.get("quality_score", 0),
            len(ra.get("verified_claims", [])),
            ra.get("word_count", 0) // 10,
        ]
        vals_b  = [
            rb.get("quality_score", 0),
            len(rb.get("verified_claims", [])),
            rb.get("word_count", 0) // 10,
        ]
        fig_cmp = go.Figure(data=[
            go.Bar(name=ta[:30], x=metrics, y=vals_a, marker_color="#3b82f6"),
            go.Bar(name=tb[:30], x=metrics, y=vals_b, marker_color="#0f766e"),
        ])
        fig_cmp.update_layout(
            barmode="group",
            title="📊 Comparison Metrics",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#475569"),
            title_font=dict(color="#0f172a", size=14),
            legend=dict(font=dict(color="#475569")),
            height=340,
            margin=dict(t=50, b=30, l=20, r=20),
        )
        st.plotly_chart(fig_cmp, use_container_width=True)
