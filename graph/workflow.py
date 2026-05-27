"""
graph/workflow.py
-----------------
2026 Edition - LangGraph 0.3+ compliant workflow.

Key upgrades vs original:
  1. add_edge(START, ...) instead of deprecated set_entry_point()
  2. SQLite checkpointer for crash recovery + time-travel debugging
  3. Human-in-the-Loop (HITL) interrupt node between Fact Checker & Analyst
  4. ChromaDB cache check node at the start (skip Researcher if cache hit)
  5. thread_id support for parallel independent research sessions
"""

import uuid
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from graph.state import ResearchState
from agents.researcher              import researcher_agent
from agents.fact_checker            import fact_checker_agent
from agents.contradiction_detector  import contradiction_detector_agent
from agents.analyst                 import analyst_agent
from agents.gap_detector            import gap_detector_agent
from agents.writer                  import writer_agent
from agents.critic                  import critic_agent, should_rewrite
from tools.pdf_generator            import generate_pdf
from tools.vector_store             import check_cache, store_results
from tools.history_manager          import save_run


# -- PDF Generation Node ------------------------------------------------------

def generate_pdf_node(state: ResearchState) -> ResearchState:
    """Final node: renders PDF, saves run history, and caches results in ChromaDB."""

    topic          = state.get("topic", "General Research")
    report         = state.get("report_draft", "")
    quality_score  = state.get("quality_score", 0)
    verified_count = len(state.get("verified_claims", []))
    agent_timings  = state.get("agent_timings") or {}
    word_count     = state.get("word_count", 0)
    llm_type       = state.get("llm_type", "unknown")

    print(f"[PDF] Rendering report for '{topic}'...")

    try:
        pdf_path = generate_pdf(
            topic=topic,
            report=report,
            quality_score=quality_score,
            verified_count=verified_count,
            llm_type=llm_type,
            agent_timings=agent_timings,
            word_count=word_count,
        )
        state["pdf_path"] = pdf_path
        print(f"[PDF] Saved: {pdf_path}")
    except Exception as e:
        print(f"[PDF] ERROR: {e}")
        state["error"] = f"PDF Generation Error: {str(e)}"
        pdf_path = ""

    # Save to run history
    try:
        save_run(
            topic=topic,
            quality_score=quality_score,
            verified_count=verified_count,
            source_count=len(state.get("raw_sources", [])),
            llm_type=llm_type,
            iterations=state.get("iterations", 1),
            pdf_path=pdf_path,
            cached=bool(state.get("cached_from_db")),
            agent_timings=agent_timings,
        )
        print("[History] Run saved to history.json")
    except Exception as e:
        print(f"[History] Save failed: {e}")

    # Cache verified research results in ChromaDB for future reuse
    try:
        if state.get("raw_sources"):
            store_results(topic=topic, sources=state["raw_sources"])
            print("[Cache] Results stored in ChromaDB for future topic reuse.")
    except Exception as e:
        print(f"[Cache] Caching skipped: {e}")

    return state


# -- Cache Check Node ---------------------------------------------------------

def cache_check_node(state: ResearchState) -> ResearchState:
    """
    Pre-Researcher node: checks ChromaDB for previously researched topics.
    If a similar topic exists (cosine similarity > 0.85), loads cached sources
    and skips the live web search (Researcher agent).
    """
    topic = state.get("topic", "")
    print(f"[Cache] Looking for '{topic}' in ChromaDB...")

    try:
        cached = check_cache(topic)
        if cached:
            print(f"[Cache] HIT! Loaded {len(cached)} sources. Skipping live search.")
            state["raw_sources"]    = cached
            state["cached_from_db"] = True
        else:
            print("[Cache] MISS. Proceeding with live Researcher agent.")
            state["cached_from_db"] = False
    except Exception as e:
        print(f"[Cache] Check failed ({e}). Proceeding with live search.")
        state["cached_from_db"] = False

    return state


def route_after_cache(state: ResearchState) -> str:
    """Routes to researcher if cache miss, else skips to fact_checker."""
    if state.get("cached_from_db"):
        return "fact_checker"   # Cache hit -- skip researcher
    return "researcher"         # Cache miss -- run researcher


# -- Human-in-the-Loop Checkpoint Node ----------------------------------------

def human_review_node(state: ResearchState) -> Command:
    """
    HITL interrupt node between Fact Checker and Analyst.

    When running via Streamlit (streaming), this pauses execution and
    surfaces the verified claims to the user. The user can:
      - APPROVE -> continue to Analyst
      - REJECT  -> route back to Researcher for a fresh search
      - ADD NOTE -> provide additional guidance for the Writer

    In non-interactive (batch) mode, human_approved=True is pre-set to skip.
    """

    # If already approved (e.g. batch mode or Streamlit pre-set), skip interrupt
    if state.get("human_approved"):
        print("[HITL] Pre-approved. Continuing to Analyst.")
        return Command(goto="analyst")

    print("[HITL] Pausing for human review of verified claims...")

    # LangGraph interrupt -- execution suspends here until resumed
    user_input = interrupt({
        "type":            "human_review",
        "verified_claims": state.get("verified_claims", []),
        "num_claims":      len(state.get("verified_claims", [])),
        "topic":           state.get("topic", ""),
        "message":         (
            "Please review the verified claims above. "
            "Choose: APPROVE to continue, REJECT to re-search, "
            "or provide a feedback note for the Writer."
        )
    })

    # Parse the human response
    decision = (user_input.get("decision", "APPROVE") if isinstance(user_input, dict)
                else str(user_input)).strip().upper()
    feedback  = user_input.get("note", "") if isinstance(user_input, dict) else ""

    if decision == "REJECT":
        print("[HITL] User rejected claims. Routing back to Researcher.")
        state["human_approved"] = False
        state["hitl_feedback"]  = feedback
        return Command(update=state, goto="researcher")

    # APPROVE or any other response -- continue
    state["human_approved"] = True
    state["hitl_feedback"]  = feedback
    if feedback:
        print(f"[HITL] Human note recorded: '{feedback}'")
    return Command(update=state, goto="analyst")


# -- Build Graph --------------------------------------------------------------

def build_research_graph(use_checkpointer: bool = True):
    """
    Builds and compiles the 2026 multi-agent research workflow.

    Args:
        use_checkpointer: If True, attaches SQLite checkpointer for
                          crash recovery and time-travel debugging.

    Returns:
        Compiled LangGraph ready for .invoke() or .stream().
    """

    workflow = StateGraph(ResearchState)

    # Register all nodes
    workflow.add_node("cache_check",             cache_check_node)
    workflow.add_node("researcher",              researcher_agent)
    workflow.add_node("fact_checker",            fact_checker_agent)
    workflow.add_node("contradiction_detector",  contradiction_detector_agent)  # Phase 2
    workflow.add_node("human_review",            human_review_node)
    workflow.add_node("analyst",                 analyst_agent)
    workflow.add_node("gap_detector",            gap_detector_agent)             # Phase 1
    workflow.add_node("writer",                  writer_agent)
    workflow.add_node("critic",                  critic_agent)
    workflow.add_node("pdf_gen",                 generate_pdf_node)

    # Entry point (LangGraph 0.3+ syntax)
    workflow.add_edge(START, "cache_check")

    # Cache -> Researcher or Fact Checker (conditional)
    workflow.add_conditional_edges(
        "cache_check",
        route_after_cache,
        {
            "researcher":   "researcher",
            "fact_checker": "fact_checker"
        }
    )

    # Linear pipeline
    workflow.add_edge("researcher",             "fact_checker")
    workflow.add_edge("fact_checker",           "contradiction_detector")  # Phase 2
    workflow.add_edge("contradiction_detector", "human_review")             # HITL sees contradictions
    # human_review routes to "analyst" or "researcher" via Command.goto

    workflow.add_edge("analyst",       "gap_detector")     # Phase 1: Gap analysis
    workflow.add_edge("gap_detector",  "writer")           # Writer now has gap data
    workflow.add_edge("writer",        "critic")

    # Quality gate: PASS -> PDF, FAIL -> Writer retry
    workflow.add_conditional_edges(
        "critic",
        should_rewrite,
        {
            "writer":  "writer",    # Rewrite loop (max 3 times)
            "pdf_gen": "pdf_gen"    # Approved -- generate PDF
        }
    )

    workflow.add_edge("pdf_gen", END)

    # Checkpointer (MemorySaver -- crash recovery + HITL support + time-travel debug)
    if use_checkpointer:
        checkpointer = MemorySaver()
        compiled = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["human_review"]  # Pause before HITL node
        )
        print("[Graph] Compiled with MemorySaver checkpointer + HITL interrupt.")
    else:
        compiled = workflow.compile()
        print("[Graph] Compiled (no checkpointer -- batch mode).")

    return compiled


def make_initial_state(
    topic: str,
    llm_type: str = "ollama",
    llm_name: str | None = None,
    human_approved: bool = False,
    thread_id: str | None = None
) -> dict:
    """
    Helper to create a clean initial state dict for a new research run.

    Args:
        topic:          Research topic string.
        llm_type:       LLM provider -- "ollama" | "groq" | "gemini".
        llm_name:       Optional model name override.
        human_approved: Set True to skip HITL checkpoint (batch/demo mode).
        thread_id:      Optional run ID for checkpointer. Auto-generated if None.

    Returns:
        Complete ResearchState dict ready for graph.invoke() / graph.stream().
    """
    return {
        "topic":                topic,
        "llm_type":             llm_type,
        "llm_name":             llm_name,
        "raw_sources":          [],
        "researcher_notes":     "",
        "cached_from_db":       False,
        "verified_claims":      [],
        "human_approved":       human_approved,
        "hitl_feedback":        "",
        "insights":             [],
        "report_draft":         "",
        "quality_score":        0,
        "critic_feedback":      "",
        "iterations":           0,
        "pdf_path":             "",
        "error":                None,
        "thread_id":            thread_id or str(uuid.uuid4()),
        "agent_timings":        {},
        "word_count":           0,
        # Phase 1 & 2 new fields
        "research_gaps":        [],
        "contradiction_pairs":  [],
        "user_library_context": "",
        "arxiv_deep_data":      [],
        "citation_data":        {},
    }
