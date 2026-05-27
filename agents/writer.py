"""
agents/writer.py
----------------
Agent 4: Writes the full structured research report.
2026 Edition: Uses ChatModel (HumanMessage), tier='powerful' for best writing quality.
Also injects HITL human reviewer notes into the writing prompt.
Upgraded: Richer prompt, anti-repetition enforcement, new Future Outlook section.
"""

from langchain_core.messages import HumanMessage
from llm.model_factory import get_llm
from graph.state import ResearchState
import time

WRITER_PROMPT = """
You are a world-class Technical Research Writer, Senior Industry Analyst, and Academic Expert commissioned to produce a definitive, authoritative research report on: "{topic}".

This report must be comprehensive enough that a reader comes away fully informed — they should NOT need to consult any other source after reading it. Think of this as a Wikipedia-level authoritative guide combined with a McKinsey-level strategic analysis.

=== STRUCTURE ===

Your report MUST follow this exact structure with all sections fully populated:

---

# Research Report: {topic}

## 1. Executive Summary
Write 5 detailed bullet points. Each bullet must be 3-4 sentences covering a distinct aspect:
concept overview, key findings, technological state, industry implications, and future direction.
Do NOT repeat any concept across bullets.

## 2. Background & Context
[2-3 paragraphs] Explain the topic from first principles. Define core terminology. Trace the historical development. Explain why this topic matters in 2025-2026. Use specific dates, names of pioneers or organizations, and foundational concepts. This section should educate a smart non-specialist reader from zero.

## 3. Key Findings
Present 12-15 critical facts and statistics. For each:
- State the finding precisely with all numbers and units.
- Show its confidence score in brackets: [Confidence: X%]
- Cite the source type in parentheses: (Source: Wikipedia / ArXiv / Web / News)
Cover: performance benchmarks, adoption statistics, cost/efficiency metrics, timeline facts, and named system/algorithm/framework facts.

## 4. Detailed Technical Analysis
[4-5 rich paragraphs, each 200+ words] Deep dive into the verified findings. Each paragraph MUST cover a DIFFERENT technical dimension:
- Paragraph 1: Core mechanisms, architectures, or scientific principles
- Paragraph 2: Current state-of-the-art systems, models, or implementations
- Paragraph 3: Performance data, comparative benchmarks, and efficiency analysis
- Paragraph 4: Challenges, limitations, and open technical problems
- Paragraph 5: Integration with adjacent technologies or fields

Include inline citations: (Source: Wikipedia), (Source: ArXiv), (Source: Web Search), (Source: News).
Do NOT repeat information across paragraphs. Each paragraph introduces progressively deeper technical details.

## 5. Statistical Highlights
A structured table or list of ALL quantitative data from the verified claims:
- Metric name | Value | Context | Source

## 6. Comparative Analysis
[2-3 paragraphs] Compare competing approaches, systems, technologies, or methodologies mentioned in the research. Use specific names. Analyze tradeoffs: speed vs. accuracy, cost vs. performance, open-source vs. proprietary, centralized vs. distributed.

## 7. Strategic Implications
5-6 concrete implications for real-world stakeholders:
- Implication 1 (for researchers / academics)
- Implication 2 (for engineers / developers)
- Implication 3 (for enterprises / organizations)
- Implication 4 (for policymakers / regulators)
- Implication 5 (for investors / market observers)
- Implication 6 (for end users / society)

## 8. Limitations & Research Gaps
[CRITICAL SECTION - USE THE IDENTIFIED GAPS BELOW]
This section is mandatory and must directly address the specific research gaps provided.
For each gap type (OPEN QUESTION, LIMITATION, FUTURE DIRECTION, CONTRADICTION, MISSING DATA),
write 2-3 sentences explaining why it matters and what resolving it would mean for the field.

{gaps_section}

## 9. Future Outlook (2025-2030)
[2-3 paragraphs] Based STRICTLY on the verified claims and the research gaps identified above:
- Where is this field headed in the next 2-5 years?
- Which of the identified open questions are closest to being answered?
- What technical or regulatory barriers must be overcome?
- Which organizations or research groups are leading the way?

## 10. Conclusion
[4-5 sentences] Synthesize the entire report: current state, most important findings, critical open problems, and why this topic will matter increasingly. Do not introduce any new information — only synthesize.

## 11. Sources & Citations
List all sources grouped by type:
### ArXiv Papers
### Wikipedia Articles
### Web Sources
### News Articles

---

=== DATA TO USE ===

VERIFIED CLAIMS:
{verified_claims}

KEY ANALYTICAL INSIGHTS:
{insights}

ADDITIONAL RESEARCH NOTES (raw fact extraction from sources):
{researcher_notes}

{feedback_section}

=== CRITICAL WRITING RULES ===

1. ANTI-REPETITION (MOST IMPORTANT): Before writing each section, mentally note all concepts already covered. NEVER restate the same fact, statistic, or idea — not even paraphrased. Each section must introduce NEW information. If you catch yourself repeating, DELETE it and write something new instead.

2. KNOWLEDGE ENRICHMENT: Use the verified claims as your factual anchors. Around them, liberally draw on your expert knowledge to explain, contextualize, and enrich — but never contradict the claims. Define technical jargon. Explain WHY each finding matters. Compare it to prior approaches. Quantify the impact where you can from your training knowledge.

3. DEPTH OVER BREVITY: This report should be long. Aim for 2500+ words total. Short, vague sections are unacceptable. Pad nothing — enrich everything.

4. TOPIC SPECIFICITY: Write specifically about "{topic}". Do not use generic filler like "this technology is important." Replace every generic statement with a specific technical fact, named system, or quantified claim.

5. PROFESSIONAL TONE: Academic yet accessible. Authoritative yet clear. No marketing fluff. No hedging ("might," "could potentially"). Use assertive, factual language.

6. CITATION INTEGRITY: Show confidence scores for all key findings. Cite source types inline for every factual claim used from the verified list.

7. RESEARCH GAPS ARE MANDATORY: Section 8 must directly use the identified gaps. Do not write generic limitation paragraphs — address each gap specifically by name and type.
"""

def writer_agent(state: ResearchState) -> ResearchState:
    """
    Agent 4: Compiles verified claims and analyst insights into a structured report.
    Uses tier='powerful' — writing quality is critical for the final output.
    Uses temperature=0.35 to encourage creative depth without hallucination.
    """
    _t0 = time.time()

    topic      = state.get("topic", "")
    llm_type   = state.get("llm_type", "ollama")
    llm_name   = state.get("llm_name")   # None = auto-select
    iterations = state.get("iterations", 0)

    print(f"[Writer] Drafting report for '{topic}' (Iteration #{iterations + 1})...")

    verified_claims  = state.get("verified_claims", [])
    insights         = state.get("insights", [])
    critic_feedback  = state.get("critic_feedback", "")
    hitl_note         = state.get("hitl_feedback", "")
    researcher_notes  = state.get("researcher_notes", "No additional research notes.")

    claims_text  = "\n".join([
        f"• {c['claim']} [Confidence: {c.get('confidence', 80)}%]"
        for c in verified_claims
    ]) if verified_claims else "No verified claims available."

    insights_text = "\n".join(insights) if insights else "No pre-calculated insights available."

    # Build feedback section (critic + HITL)
    feedback_parts = []
    if iterations > 0 and critic_feedback:
        feedback_parts.append(f"""========================================
CRITIC FEEDBACK FROM PREVIOUS DRAFT (MUST ADDRESS ALL POINTS):
{critic_feedback}

Address each bullet point above explicitly in this new draft.
========================================""")

    if hitl_note:
        feedback_parts.append(f"""========================================
HUMAN REVIEWER GUIDANCE (HIGHEST PRIORITY):
{hitl_note}

Incorporate this guidance throughout the report.
========================================""")

    feedback_section = "\n\n".join(feedback_parts)

    # Inject research gaps for Section 8 (Limitations & Research Gaps)
    research_gaps = state.get("research_gaps", [])
    if research_gaps:
        gap_lines = "\n".join(f"  - {g}" for g in research_gaps)
        gaps_section = f"""IDENTIFIED RESEARCH GAPS (must be incorporated into Section 8):
{gap_lines}"""
    else:
        gaps_section = "No pre-identified research gaps available. Derive limitations from the verified claims."

    prompt_text = WRITER_PROMPT.format(
        topic=topic,
        verified_claims=claims_text,
        insights=insights_text,
        researcher_notes=researcher_notes,
        feedback_section=feedback_section,
        gaps_section=gaps_section,
    )

    # Powerful tier with higher temperature for creative, rich writing
    llm = get_llm(model_type=llm_type, model_name=llm_name, tier="powerful", temperature=0.35)
    response = llm.invoke([HumanMessage(content=prompt_text)])

    # Extract string from AIMessage
    response_text = response.content if hasattr(response, "content") else str(response)

    state["report_draft"] = response_text
    state["iterations"]   = iterations + 1
    state["word_count"]   = len(response_text.split())

    elapsed = round(time.time() - _t0, 2)
    timings = state.get("agent_timings") or {}
    timings[f"writer_{state['iterations']}"] = elapsed
    state["agent_timings"] = timings

    print(f"[Writer] Draft completed (Iteration #{state['iterations']}, {state['word_count']} words, {elapsed}s).")
    return state
