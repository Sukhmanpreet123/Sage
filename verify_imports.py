import sys
import os

print("--- Checking Project Module Structure and Imports ---")

try:
    from graph.state import ResearchState
    print("[OK] import ResearchState: SUCCESS")
except Exception as e:
    print(f"[FAIL] import ResearchState: FAILED ({e})")

try:
    from llm.model_factory import get_llm
    print("[OK] import get_llm: SUCCESS")
except Exception as e:
    print(f"[FAIL] import get_llm: FAILED ({e})")

try:
    from tools.search_tools import web_search, wikipedia_search, arxiv_search, rss_news_search
    print("[OK] import search_tools: SUCCESS")
except Exception as e:
    print(f"[FAIL] import search_tools: FAILED ({e})")

try:
    from tools.pdf_generator import generate_pdf
    print("[OK] import generate_pdf: SUCCESS")
except Exception as e:
    print(f"[FAIL] import generate_pdf: FAILED ({e})")

try:
    from agents.researcher import researcher_agent
    from agents.fact_checker import fact_checker_agent
    from agents.analyst import analyst_agent
    from agents.writer import writer_agent
    from agents.critic import critic_agent, should_rewrite
    print("[OK] import all 5 agents: SUCCESS")
except Exception as e:
    print(f"[FAIL] import agents: FAILED ({e})")

try:
    from graph.workflow import build_research_graph
    print("[OK] import build_research_graph: SUCCESS")
except Exception as e:
    print(f"[FAIL] import build_research_graph: FAILED ({e})")

print("-----------------------------------------------------")
