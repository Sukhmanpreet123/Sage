"""
agents/critic.py
----------------
Agent 5: Quality gate — scores the report and decides PASS or REWRITE.
2026 Edition: Uses ChatModel (HumanMessage), tier='powerful' for strict judgment.
"""

from langchain_core.messages import HumanMessage
from llm.model_factory import get_llm
from graph.state import ResearchState
import time

CRITIC_PROMPT = """
You are an uncompromising Editorial Director and Lead Fact-Reviewer. Your job is to strictly evaluate the draft research report and assign quality scores based on the facts provided.

Research Topic: {topic}

DRAFT REPORT TO EVALUATE:
{report_draft}

REFERENCE VERIFIED CLAIMS:
{verified_claims}

Please rate the draft on these three metrics (each scored 0 to 100):
1. ACCURACY (40 points weight): Does the report contain only verified claims? Are there hallucinated figures or extrapolations? Deduct heavily for any facts not in the list.
2. COMPLETENESS (30 points weight): Does it cover the main angles? Are all important quantitative metrics from verified claims incorporated?
3. CLARITY (30 points weight): Is the structure clean and professional? Is it readable and does it follow academic style?

You must calculate the final WEIGHTED_TOTAL as follows:
WEIGHTED_TOTAL = (ACCURACY_SCORE * 0.40) + (COMPLETENESS_SCORE * 0.30) + (CLARITY_SCORE * 0.30)

Respond strictly in the following format. Do NOT deviate. Do NOT include markdown styling or outer quotes.

ACCURACY_SCORE: [0-100]
COMPLETENESS_SCORE: [0-100]
CLARITY_SCORE: [0-100]
WEIGHTED_TOTAL: [0-100 calculated total]
DECISION: [PASS if total >= 70 else REWRITE]
FEEDBACK: [List bullet points describing exactly what needs to be added, corrected, or styled if REWRITE, or general praise if PASS]
"""

def critic_agent(state: ResearchState) -> ResearchState:
    """
    Agent 5: Evaluates the draft quality. Rejects scores below 70 and demands a rewrite.
    Uses tier='powerful' — quality judgment requires careful reasoning.
    """
    _t0 = time.time()

    topic    = state.get("topic", "")
    llm_type = state.get("llm_type", "ollama")
    llm_name = state.get("llm_name")   # None = auto-select

    print(f"[Critic] Scoring report quality for '{topic}'...")

    report_draft    = state.get("report_draft", "")
    verified_claims = state.get("verified_claims", [])

    if not report_draft:
        print("[Critic] No report draft found. Auto-reject.")
        state["quality_score"]   = 0
        state["critic_feedback"] = "Draft is empty. A complete rewrite is required."
        return state

    claims_text = "\n".join([
        f"• {c['claim']} (Confidence: {c.get('confidence', 80)}%)"
        for c in verified_claims
    ])

    prompt_text = CRITIC_PROMPT.format(
        topic=topic,
        report_draft=report_draft,
        verified_claims=claims_text
    )

    # Powerful tier — quality judgment is the most critical reasoning step
    llm = get_llm(model_type=llm_type, model_name=llm_name, tier="powerful")
    response = llm.invoke([HumanMessage(content=prompt_text)])

    # Extract string from AIMessage
    response_text = response.content if hasattr(response, "content") else str(response)

    score    = parse_critic_score(response_text)
    feedback = extract_feedback(response_text)

    state["quality_score"]   = score
    state["critic_feedback"] = feedback

    elapsed = round(time.time() - _t0, 2)
    timings = state.get("agent_timings") or {}
    timings["critic"] = elapsed
    state["agent_timings"] = timings

    print(f"[Critic] Score {score}/100 -> {'PASS' if score >= 70 else 'REWRITE'} ({elapsed}s)")
    return state

def parse_critic_score(text: str) -> int:
    """Extract the weighted total score from critic output"""
    for line in text.split("\n"):
        line = line.strip()
        if "WEIGHTED_TOTAL:" in line:
            try:
                score_str = line.split(":")[1].strip()
                # Remove brackets or percentage symbols
                score_str = "".join(c for c in score_str if c.isdigit() or c == '.')
                return int(float(score_str))
            except Exception:
                pass
    return 75  # Default fallback if parsing fails

def extract_feedback(text: str) -> str:
    """Extract improvement feedback"""
    feedback_lines = []
    found_feedback = False
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("FEEDBACK:"):
            feedback_lines.append(line.replace("FEEDBACK:", "").strip())
            found_feedback = True
        elif found_feedback:
            feedback_lines.append(line)
            
    feedback_text = "\n".join(feedback_lines).strip()
    return feedback_text if feedback_text else "Keep up the good writing style."

def should_rewrite(state: ResearchState) -> str:
    """Conditional router function for LangGraph node routing"""
    iterations = state.get("iterations", 0)
    score = state.get("quality_score", 0)

    if score < 70 and iterations < 3:
        print(f"[Critic] Route: Quality score {score} < 70, Iteration {iterations} < 3. ROUTING BACK TO WRITER.")
        return "writer"
    else:
        print(f"[Critic] Route: Quality score {score} >= 70 or Max iterations reached. ROUTING TO PDF_GEN.")
        return "pdf_gen"
