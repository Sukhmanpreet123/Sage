"""
agents/gap_detector.py
----------------------
Phase 1 Feature: Research Gap Detector Agent

This agent sits AFTER the Analyst and BEFORE the Writer in the LangGraph pipeline.
Its sole purpose is to answer the question: "What does this research NOT tell us?"

It outputs:
  - Open/unanswered questions the research raises
  - Identified limitations in existing findings
  - Specific future research directions scholars could pursue
  - Internal contradictions or conflicts between verified claims

Output is stored in state["research_gaps"] as a list of strings.
The Writer agent receives these gaps and weaves them into the report's
Limitations and Future Scope sections, making the report far more academically credible.
"""

from langchain_core.messages import HumanMessage
from llm.model_factory import get_llm
from graph.state import ResearchState
import time

GAP_DETECTOR_PROMPT = """
You are a world-class academic Research Gap Analyst with expertise in identifying the frontiers and limitations of scientific knowledge. Your role is NOT to summarize what is known — that has already been done.

Your role is ONLY to identify what is UNKNOWN, UNCERTAIN, or UNANSWERED.

Research Topic: "{topic}"

Verified Claims (what IS known):
{verified_claims}

Analyst Insights:
{insights}

Perform a rigorous gap analysis. For each gap you identify, specify its TYPE:

TYPES:
- [OPEN QUESTION]: A specific question that the research raises but does NOT answer.
- [LIMITATION]: A methodological, data, or scope limitation in the current research.
- [CONTRADICTION]: Two claims that conflict with or undermine each other.
- [FUTURE DIRECTION]: A concrete, actionable research direction that would advance this field.
- [MISSING DATA]: A key piece of information that was NOT found but would be crucial for understanding.

RULES:
1. Identify EXACTLY 8-12 gaps. Not more, not less.
2. Every gap must be SPECIFIC — never vague. Include the actual topic, numbers, or concepts being referenced.
3. Gaps must be directly derived from the verified claims provided — do not invent claims.
4. Each gap must be a standalone, fully readable sentence (no fragments).

OUTPUT FORMAT — respond STRICTLY as a numbered list with the TYPE prefix:
1. [OPEN QUESTION] ...
2. [LIMITATION] ...
3. [FUTURE DIRECTION] ...
(continue...)

Do NOT include any introduction, conclusion, or headers. ONLY the numbered list.
"""


def gap_detector_agent(state: ResearchState) -> ResearchState:
    """
    Phase 1 Agent: Research Gap Detector.

    Analyzes verified claims + analyst insights to surface what the research
    does NOT answer — open questions, limitations, contradictions, and future
    research directions.

    Runs after Analyst, before Writer.
    Outputs: state["research_gaps"] as List[str]
    """
    _t0 = time.time()

    topic            = state.get("topic", "")
    verified_claims  = state.get("verified_claims", [])
    insights         = state.get("insights", [])
    llm_type         = state.get("llm_type", "ollama")
    llm_name         = state.get("llm_name")

    print(f"[GapDetector] Analyzing research gaps for '{topic}'...")

    # Build verified claims text
    if verified_claims:
        claims_text = "\n".join([
            f"  {i+1}. {c.get('claim', '')} (Confidence: {c.get('confidence', 0)}%)"
            for i, c in enumerate(verified_claims)
        ])
    else:
        claims_text = "No verified claims available."

    # Build insights text
    if insights:
        insights_text = "\n".join([
            f"  - {line}" for line in insights if line.strip()
        ])
    else:
        insights_text = "No analyst insights available."

    if not verified_claims and not insights:
        print("[GapDetector] No data to analyze. Skipping.")
        state["research_gaps"] = [
            "[LIMITATION] Insufficient verified data was collected to perform a comprehensive gap analysis."
        ]
        return state

    # Use the fast-tier model — gap detection is a focused reasoning task
    llm = get_llm(model_type=llm_type, model_name=llm_name, tier="fast")

    prompt = GAP_DETECTOR_PROMPT.format(
        topic=topic,
        verified_claims=claims_text,
        insights=insights_text,
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content if hasattr(response, "content") else str(response)

        # Parse the numbered list into individual gap strings
        gaps = []
        for line in response_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Strip leading numbers like "1. ", "10. "
            import re
            cleaned = re.sub(r"^\d+\.\s*", "", line).strip()
            if cleaned and len(cleaned) > 10:
                gaps.append(cleaned)

        # Fallback if parsing yields nothing
        if not gaps:
            gaps = [response_text.strip()]

        state["research_gaps"] = gaps
        print(f"[GapDetector] Identified {len(gaps)} research gaps.")

    except Exception as e:
        print(f"[GapDetector] ERROR: {e}")
        state["research_gaps"] = [
            f"[LIMITATION] Gap analysis could not be completed due to: {str(e)}"
        ]

    # Record timing
    elapsed = round(time.time() - _t0, 2)
    timings = state.get("agent_timings") or {}
    timings["gap_detector"] = elapsed
    state["agent_timings"] = timings

    print(f"[GapDetector] Completed in {elapsed}s.")
    return state
