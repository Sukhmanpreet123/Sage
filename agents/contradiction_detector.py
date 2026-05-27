"""
agents/contradiction_detector.py
---------------------------------
Phase 2 Feature: Contradiction Detector Agent

Runs AFTER the Fact Checker and BEFORE Human Review.
Detects two categories of contradictions:

1. INTERNAL contradictions: Verified claims that conflict with each other
   within the current research run (e.g., two claims with opposite numbers).

2. LIBRARY contradictions: New verified claims that contradict material in
   the user's personal research library (if a library has been uploaded).
   This is extremely powerful for researchers: "This new paper contradicts
   your thesis from March."

Output stored in state["contradiction_pairs"] as List[ContradictionPair].
These are surfaced in the HITL checkpoint UI so users can review before
approving the pipeline to proceed to the Analyst.
"""

from langchain_core.messages import HumanMessage
from llm.model_factory import get_llm
from graph.state import ResearchState, ContradictionPair
import re
import time

INTERNAL_CONTRADICTION_PROMPT = """
You are an expert Academic Fact Auditor specializing in identifying logical contradictions and factual conflicts within a set of research claims.

Research Topic: "{topic}"

Below is the complete list of verified research claims for this topic:

{claims_text}

Your task: Carefully analyze every claim pair combination and identify any genuine factual contradictions — statements that cannot both be true simultaneously.

TYPES of contradictions to detect:
- NUMERICAL: Two claims cite different statistics for the same metric (e.g., "adoption is 40%" vs "adoption is 72%")
- CAUSAL: Two claims describe opposite cause-effect relationships
- TEMPORAL: Two claims make conflicting statements about timing or chronology
- METHODOLOGICAL: Two claims describe conflicting approaches as the best
- ATTRIBUTIVE: Authorship, invention credit, or organizational ownership conflicts

RULES:
1. Only flag GENUINE contradictions — not just different topics or perspectives.
2. A contradiction must involve the same subject and same attribute with conflicting values.
3. Be specific: quote the exact language from each contradicting claim.
4. Rate severity: HIGH (directly contradicting factual numbers/dates), MEDIUM (conflicting frameworks or positions), LOW (minor discrepancies in framing).
5. If you find NO genuine contradictions, respond with exactly: NO_CONTRADICTIONS_FOUND

OUTPUT FORMAT (repeat for each contradiction found):
CONTRADICTION_START
CLAIM_A: [exact claim text]
CLAIM_B: [exact contradicting claim text]
EXPLANATION: [precise explanation of why these conflict]
SEVERITY: [HIGH / MEDIUM / LOW]
SOURCE: internal
CONTRADICTION_END
"""

LIBRARY_CONTRADICTION_PROMPT = """
You are an expert Academic Fact Auditor tasked with finding conflicts between NEW research findings and an EXISTING knowledge base (the user's personal research library).

Research Topic: "{topic}"

NEW VERIFIED CLAIMS (from this research run):
{claims_text}

USER'S EXISTING LIBRARY CONTENT (documents the user previously uploaded):
{library_context}

Your task: Identify cases where the new research CONTRADICTS what is in the user's existing library.

This is especially important for:
- Updated statistics that supersede older numbers
- New experimental results that refute previously accepted claims
- Theoretical positions that challenge established frameworks in the user's documents

RULES:
1. Only flag genuine, specific contradictions — not just different levels of detail.
2. Quote the specific new claim AND the specific library passage it contradicts.
3. Rate severity: HIGH (direct numerical/factual conflict), MEDIUM (methodological or positional conflict), LOW (minor discrepancy).
4. If no contradictions exist between new findings and library, respond with exactly: NO_CONTRADICTIONS_FOUND

OUTPUT FORMAT:
CONTRADICTION_START
CLAIM_A: [exact new verified claim that contradicts library]
CLAIM_B: [exact passage from library that is contradicted]
EXPLANATION: [why these conflict and what the implication is]
SEVERITY: [HIGH / MEDIUM / LOW]
SOURCE: library
CONTRADICTION_END
"""


def _parse_contradiction_blocks(text: str) -> list[ContradictionPair]:
    """Parse the LLM output into structured ContradictionPair dicts."""
    if "NO_CONTRADICTIONS_FOUND" in text.upper():
        return []

    pairs = []
    # Split on CONTRADICTION_START blocks
    blocks = re.split(r"CONTRADICTION_START", text, flags=re.IGNORECASE)

    for block in blocks[1:]:  # Skip first empty segment
        end_match = re.search(r"CONTRADICTION_END", block, re.IGNORECASE)
        if end_match:
            block = block[:end_match.start()]

        pair = {"claim_a": "", "claim_b": "", "explanation": "", "severity": "medium", "source": "internal"}

        for line in block.strip().split("\n"):
            line = line.strip()
            if line.upper().startswith("CLAIM_A:"):
                pair["claim_a"] = line[8:].strip()
            elif line.upper().startswith("CLAIM_B:"):
                pair["claim_b"] = line[8:].strip()
            elif line.upper().startswith("EXPLANATION:"):
                pair["explanation"] = line[12:].strip()
            elif line.upper().startswith("SEVERITY:"):
                sev = line[9:].strip().lower()
                pair["severity"] = sev if sev in ("high", "medium", "low") else "medium"
            elif line.upper().startswith("SOURCE:"):
                src = line[7:].strip().lower()
                pair["source"] = src if src in ("internal", "library") else "internal"

        if pair["claim_a"] and pair["claim_b"] and pair["explanation"]:
            pairs.append(pair)

    return pairs


def contradiction_detector_agent(state: ResearchState) -> ResearchState:
    """
    Phase 2 Agent: Contradiction Detector.

    Finds:
    1. Internal contradictions between verified claims.
    2. Library contradictions (new claims vs user's uploaded documents).

    Runs after Fact Checker, before Human Review.
    Outputs: state["contradiction_pairs"] as List[ContradictionPair]
    """
    _t0 = time.time()

    topic           = state.get("topic", "")
    verified_claims = state.get("verified_claims", [])
    library_context = state.get("user_library_context", "")
    llm_type        = state.get("llm_type", "ollama")
    llm_name        = state.get("llm_name")

    print(f"[ContradictionDetector] Scanning for contradictions in '{topic}'...")

    all_pairs = []

    if not verified_claims:
        print("[ContradictionDetector] No verified claims — skipping.")
        state["contradiction_pairs"] = []
        return state

    # Build claims text
    claims_text = "\n".join([
        f"  [{i+1}] {c.get('claim', '')} [Conf: {c.get('confidence', 0)}%]"
        for i, c in enumerate(verified_claims)
    ])

    # Use fast model — contradiction detection is pattern-matching, not deep reasoning
    llm = get_llm(model_type=llm_type, model_name=llm_name, tier="fast")

    # ── Pass 1: Internal Contradiction Scan ───────────────────────────────────
    if len(verified_claims) >= 2:
        try:
            print("[ContradictionDetector] Running internal contradiction scan...")
            prompt = INTERNAL_CONTRADICTION_PROMPT.format(
                topic=topic,
                claims_text=claims_text
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content if hasattr(response, "content") else str(response)
            internal_pairs = _parse_contradiction_blocks(response_text)
            all_pairs.extend(internal_pairs)
            print(f"[ContradictionDetector] Found {len(internal_pairs)} internal contradictions.")
        except Exception as e:
            print(f"[ContradictionDetector] Internal scan error: {e}")

    # ── Pass 2: Library Contradiction Scan (only if library uploaded) ─────────
    if library_context and len(library_context.strip()) > 100:
        try:
            print("[ContradictionDetector] Running library contradiction scan...")
            # Truncate library context to avoid prompt overflow
            lib_preview = library_context[:3000]

            prompt = LIBRARY_CONTRADICTION_PROMPT.format(
                topic=topic,
                claims_text=claims_text,
                library_context=lib_preview
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content if hasattr(response, "content") else str(response)
            library_pairs = _parse_contradiction_blocks(response_text)
            all_pairs.extend(library_pairs)
            print(f"[ContradictionDetector] Found {len(library_pairs)} library contradictions.")
        except Exception as e:
            print(f"[ContradictionDetector] Library scan error: {e}")
    else:
        print("[ContradictionDetector] No user library loaded — skipping library scan.")

    state["contradiction_pairs"] = all_pairs

    elapsed = round(time.time() - _t0, 2)
    timings = state.get("agent_timings") or {}
    timings["contradiction_detector"] = elapsed
    state["agent_timings"] = timings

    total = len(all_pairs)
    high_sev = sum(1 for p in all_pairs if p.get("severity") == "high")
    print(f"[ContradictionDetector] Total: {total} contradictions ({high_sev} HIGH severity) in {elapsed}s.")
    return state
