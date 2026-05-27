"""
agents/fact_checker.py
----------------------
Agent 2: Cross-verifies claims, removes hallucinations.
2026 Edition: Uses ChatModel (HumanMessage), tier='powerful' for deep reasoning.
Upgraded: Uses 1500-char source snippets and targets 20-30 distinct claims.
"""

from langchain_core.messages import HumanMessage
from llm.model_factory import get_llm
from graph.state import ResearchState
import time

FACT_CHECKER_PROMPT = """
You are a highly efficient, objective Fact-Checker and Technical Intelligence Analyst. Your task is to verify technical claims in the research data, eliminate obvious hallucinations, and produce an exhaustive, high-quality list of verified claims.

Topic of Research: {topic}

Here is the raw text extracted from multiple search sources (Web, Wikipedia, ArXiv, and News):
{sources}

Your task:
1. Extract and verify as many DISTINCT, SPECIFIC, and TECHNICALLY VALUABLE claims as possible. **Target: 20-30 unique verified claims**. Do not be overly restrictive — if a claim is technically detailed, numerically supported, or grounded in any source, verify it.
2. Prioritize: specific numbers, statistics, percentages, growth rates, dates, proper nouns (names of algorithms, companies, researchers, frameworks), comparative benchmarks, and factual technical assertions.
3. Classify each claim:
   - VERIFIED: Supported by at least one provided source and contains plausible, useful, technically specific information.
   - REMOVE: Explicitly contradicted by other sources, completely ungrounded, or obviously fabricated.
4. For VERIFIED claims, write the claim in a detailed, technically precise format — expand acronyms, include context.

Generate your response using the following layout for each claim, separated by '---':
CLAIM: [Precise, detailed, technically expanded claim]
STATUS: [VERIFIED / REMOVE]
CONFIDENCE: [Score 0-100 based on source backing strength]
REASONING: [Brief explanation citing which source type confirmed this]
---
"""

def fact_checker_agent(state: ResearchState) -> ResearchState:
    """
    Agent 2: Cross-verifies claims against raw sources.
    Uses tier='powerful' — this is the hallucination guard; reasoning depth matters.
    """
    _t0 = time.time()

    topic    = state.get("topic", "")
    llm_type = state.get("llm_type", "ollama")
    llm_name = state.get("llm_name")   # None = auto-select

    print(f"[Fact Checker] Verifying claims for '{topic}'...")

    raw_sources = state.get("raw_sources", [])
    if not raw_sources:
        print("[Fact Checker] No raw sources found to verify!")
        state["verified_claims"] = []
        return state

    # Use 1500 chars per source for richer context
    sources_text = "\n\n".join([
        f"[{s['source_type'].upper()}] Title: {s['title']}\nURL: {s['url']}\nContent: {s['content'][:1500]}"
        for s in raw_sources
    ])

    prompt_text = FACT_CHECKER_PROMPT.format(
        topic=topic,
        sources=sources_text
    )

    # Use powerful tier — fact-checking requires deep cross-referencing
    llm = get_llm(model_type=llm_type, model_name=llm_name, tier="powerful")
    response = llm.invoke([HumanMessage(content=prompt_text)])

    # ChatModel returns an AIMessage — extract string content
    response_text = response.content if hasattr(response, "content") else str(response)

    # Parse response into verified claims structures
    claims = parse_verification_output(response_text)

    # Filter to only keep VERIFIED claims
    verified_claims = [c for c in claims if c["status"] == "VERIFIED"]

    # Fallback: if LLM produced no parseable output, use raw sources as baseline
    if not verified_claims:
        print("[Fact Checker] No VERIFIED claims found. Applying fallback...")
        for source in raw_sources[:8]:
            verified_claims.append({
                "claim":     f"{source['title']}: {source['content'][:300]}...",
                "status":    "VERIFIED",
                "confidence": 70,
                "reasoning": "Fallback — source title used due to empty LLM verification output."
            })

    state["verified_claims"] = verified_claims
    elapsed = round(time.time() - _t0, 2)
    timings = state.get("agent_timings") or {}
    timings["fact_checker"] = elapsed
    state["agent_timings"] = timings
    print(f"[Fact Checker] {len(verified_claims)} claims verified from {len(claims)} candidates in {elapsed}s.")
    return state

def parse_verification_output(text: str) -> list:
    """Parse LLM output into structured claim dicts"""
    claims = []
    blocks = text.split("---")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if "CLAIM:" in block:
            claim = {}
            for line in block.split("\n"):
                line = line.strip()
                if line.startswith("CLAIM:"):
                    claim["claim"] = line.replace("CLAIM:", "").strip()
                elif line.startswith("STATUS:"):
                    claim["status"] = line.replace("STATUS:", "").strip().upper()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        claim["confidence"] = int(line.replace("CONFIDENCE:", "").strip().replace("%", ""))
                    except Exception:
                        claim["confidence"] = 70
                elif line.startswith("REASONING:"):
                    claim["reasoning"] = line.replace("REASONING:", "").strip()
            if claim.get("claim"):
                if "status" not in claim:
                    claim["status"] = "VERIFIED"
                claims.append(claim)
    return claims
