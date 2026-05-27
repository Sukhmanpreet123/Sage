"""
graph/state.py
--------------
2026 Edition: Extended ResearchState TypedDict.

New fields added:
  - human_approved        : HITL checkpoint — human reviewed verified claims
  - cached_from_db        : Indicates ChromaDB cache was used (skipped live search)
  - thread_id             : Unique run identifier for SQLite checkpointer
  - hitl_feedback         : Optional human notes added at the HITL checkpoint
  - research_gaps         : [Phase 1] Gap Detector agent output
  - contradiction_pairs   : [Phase 2] Contradiction Detector agent output
  - user_library_context  : [Phase 2] Merged relevant text from user's PDF library
  - arxiv_deep_data       : [Phase 2] Full section extracts from ArXiv papers
  - citation_data         : [Phase 2] Citation graph data from Semantic Scholar
"""

from typing import TypedDict, List, Optional, Dict, Any


class SourceItem(TypedDict):
    """Raw source collected by the Researcher agent."""
    title:       str
    content:     str
    url:         str
    source_type: str   # "web" | "wikipedia" | "arxiv" | "news"


class VerifiedClaim(TypedDict):
    """A single fact that passed Fact Checker verification."""
    claim:      str
    status:     str          # "VERIFIED" | "UNCERTAIN" | "REMOVED"
    confidence: int          # 0–100
    reasoning:  Optional[str]


class ContradictionPair(TypedDict):
    """A pair of contradicting claims found by the Contradiction Detector."""
    claim_a:     str
    claim_b:     str
    explanation: str
    severity:    str   # "high" | "medium" | "low"
    source:      str   # "internal" | "library"


class ResearchState(TypedDict):
    """
    Shared state object that flows through every node in the LangGraph.
    Every agent reads from and writes to this state.
    """

    # ── Input ────────────────────────────────────────────────────────────────
    topic:          str                      # User's research topic
    llm_type:       Optional[str]            # "ollama" | "groq" | "gemini"
    llm_name:       Optional[str]            # Model name override (optional)

    # ── Agent 1 Output ───────────────────────────────────────────────────────
    raw_sources:    List[SourceItem]         # 15-20 items from all sources

    # ── Researcher LLM Extraction ─────────────────────────────────────────────
    researcher_notes: Optional[str]          # Researcher's LLM fact-extraction text

    # ── Agentic RAG ──────────────────────────────────────────────────────────
    cached_from_db: Optional[bool]           # True if loaded from ChromaDB cache

    # ── Agent 2 Output ───────────────────────────────────────────────────────
    verified_claims: List[VerifiedClaim]     # Only VERIFIED items pass forward

    # ── Human-in-the-Loop (HITL) ─────────────────────────────────────────────
    human_approved:  Optional[bool]          # Set to True after human review
    hitl_feedback:   Optional[str]           # Optional human notes for the Writer

    # ── Agent 3 Output ───────────────────────────────────────────────────────
    insights:        List[str]               # Bullet-point analysis lines

    # ── Agent 4 Output ───────────────────────────────────────────────────────
    report_draft:    str                     # Full report in Markdown

    # ── Agent 5 Output ───────────────────────────────────────────────────────
    quality_score:   int                     # 0–100 weighted score
    critic_feedback: str                     # Specific improvement notes

    # ── Control ──────────────────────────────────────────────────────────────
    iterations:      int                     # Times Writer has run (max 3)

    # ── Final Output ─────────────────────────────────────────────────────────
    pdf_path:        str                     # Path to generated PDF

    # ── Error Handling ───────────────────────────────────────────────────────
    error:           Optional[str]           # Last error message (if any)

    # ── Checkpointing ────────────────────────────────────────────────────────
    thread_id:       Optional[str]           # Unique run ID for SQLite saver

    # ── Performance Analytics ─────────────────────────────────────
    agent_timings:   Optional[Dict[str, float]]  # Agent name -> seconds taken
    word_count:      Optional[int]               # Final report word count

    # ── Phase 1: Research Gap Detector ───────────────────────────────────────
    research_gaps:   Optional[List[str]]         # Open questions & future directions

    # ── Phase 2: Contradiction Detector ──────────────────────────────────────
    contradiction_pairs: Optional[List[ContradictionPair]]  # Conflicting claim pairs

    # ── Phase 2: Personal Research Library ───────────────────────────────────
    user_library_context: Optional[str]          # Top chunks from user's PDF library

    # ── Phase 2: ArXiv Deep Mode ─────────────────────────────────────────────
    arxiv_deep_data: Optional[List[Dict[str, Any]]]  # Full section extracts per paper

    # ── Phase 2: Citation Graph ───────────────────────────────────────────────
    citation_data:   Optional[Dict[str, Any]]    # Raw citation records for rendering
