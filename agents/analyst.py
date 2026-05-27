"""
agents/analyst.py
-----------------
Agent 3: Extracts structured insights from verified claims.
2026 Edition: Uses ChatModel (HumanMessage), tier='powerful' for deeper synthesis.
Upgraded: Richer prompt, identifies cross-claim patterns and implications.
"""

from langchain_core.messages import HumanMessage
from llm.model_factory import get_llm
from graph.state import ResearchState
import time

ANALYST_PROMPT = """
You are a Senior Research Analyst and Domain Intelligence Expert with 20 years of experience synthesizing technical knowledge across academia, industry, and policy. Your job is to extract deeply structured, non-obvious insights from verified research claims.

Research Topic: {topic}

Verified Claims (with confidence scores):
{verified_claims}

Perform the following analysis — be EXHAUSTIVE and SPECIFIC. Back every point with exact claim data:

1. KEY STATISTICS & QUANTITATIVE BENCHMARKS:
   - List every number, percentage, date, growth rate, size metric, speed, or cost figure.
   - Include context for each number (what it measures, why it matters).

2. MAJOR TECHNOLOGY TRENDS & PARADIGM SHIFTS:
   - Identify 4-6 major directional trends that emerge across multiple claims.
   - For each trend: explain its origin, current state, and projected direction.

3. COMPARATIVE ANALYSIS:
   - Contrast traditional approaches vs. emerging ones.
   - Compare competing frameworks, methodologies, or systems mentioned in the claims.
   - Identify where the field is converging and where it is fragmenting.

4. CROSS-CLAIM CONNECTIONS:
   - Identify hidden relationships or dependencies between different claims.
   - Highlight where claim A enables or constrains claim B.

5. CRITICAL STRATEGIC IMPLICATIONS:
   - 4-6 specific implications for practitioners, researchers, organizations, or policymakers.
   - Ground each implication directly in the verified claims.

6. KNOWLEDGE GAPS & OPEN QUESTIONS:
   - What important questions remain unanswered given the claims?
   - What areas need more research or verification?

Format your output using clean, hierarchical markdown:

## Key Statistics & Quantitative Benchmarks
- [stat with context]

## Major Trends & Paradigm Shifts
- [trend with explanation]

## Comparative Analysis
- [comparison]

## Cross-Claim Connections
- [connection]

## Strategic Implications
- [implication grounded in specific claim data]

## Knowledge Gaps & Open Questions
- [gap or question]

Be technically precise. Do NOT extrapolate beyond the claims. Do NOT repeat the same point under different headings.
"""

def analyst_agent(state: ResearchState) -> ResearchState:
    """
    Agent 3: Extracts structured insights from verified claims.
    Uses tier='powerful' — deep synthesis requires the strongest reasoning model.
    """
    _t0 = time.time()

    topic    = state.get("topic", "")
    llm_type = state.get("llm_type", "ollama")
    llm_name = state.get("llm_name")   # None = auto-select

    print(f"[Analyst] Extracting insights for '{topic}'...")

    verified_claims = state.get("verified_claims", [])
    if not verified_claims:
        print("[Analyst] No verified claims. Populating default structure.")
        state["insights"] = [
            "## Key Statistics",
            "- No quantitative statistics were verified in this run.",
            "## Major Trends",
            "- Qualitative trends unavailable — insufficient source material.",
            "## Strategic Implications",
            "- Refine the topic or expand search parameters to gather insights."
        ]
        return state

    # Include HITL human feedback if provided
    hitl_note = state.get("hitl_feedback", "")
    hitl_section = f"\n\nHUMAN REVIEWER GUIDANCE:\n{hitl_note}" if hitl_note else ""

    claims_text = "\n".join([
        f"• {c['claim']} (Confidence: {c.get('confidence', 80)}%)"
        for c in verified_claims
    ])

    prompt_text = ANALYST_PROMPT.format(
        topic=topic,
        verified_claims=claims_text + hitl_section
    )

    # Powerful tier — deep synthesis requires the strongest reasoning model
    llm = get_llm(model_type=llm_type, model_name=llm_name, tier="powerful")
    response = llm.invoke([HumanMessage(content=prompt_text)])

    # Extract string from AIMessage
    response_text = response.content if hasattr(response, "content") else str(response)

    state["insights"] = response_text.split("\n")
    elapsed = round(time.time() - _t0, 2)
    timings = state.get("agent_timings") or {}
    timings["analyst"] = elapsed
    state["agent_timings"] = timings
    print(f"[Analyst] Extracted {len(state['insights'])} insight lines in {elapsed}s.")
    return state
