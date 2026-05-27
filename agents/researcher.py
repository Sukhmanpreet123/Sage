"""
agents/researcher.py
--------------------
Agent 1: Gathers raw information from multiple free sources.
2026 Edition: Uses ChatModel (HumanMessage), tier='fast' for speed.
Upgraded with Smart Query Reformulation/Expansion to maximize source depth.
"""

from langchain_core.messages import HumanMessage
from tools.search_tools import web_search, wikipedia_search, arxiv_search, rss_news_search, pubmed_search, openalex_search
from llm.model_factory import get_llm
from graph.state import ResearchState
import time

QUERY_EXPANSION_PROMPT = """
You are an expert Research Query Optimizer. Given a research topic, generate 6 optimized search queries tailored for different platforms to fetch the deepest, most comprehensive, and non-repetitive technical information.

Research Topic: "{topic}"

Respond STRICTLY in this exact format. Do NOT write any conversational intro or extra text:
WIKI_QUERY: [One broad, high-level encyclopedia concept, 1-2 keywords]
ARXIV_QUERY: [2-3 scientific/academic keywords focusing on core research fields, theories, or technologies]
WEB_QUERY: [An up-to-date query focusing on 2026 developments, trends, roadmaps, and breakthroughs]
NEWS_QUERY: [A single core keyword to filter active RSS news feeds]
PUBMED_QUERY: [2-3 biomedical or life sciences keywords focusing on genes, treatments, clinical or chemical concepts]
OPENALEX_QUERY: [2-3 broader academic keywords focusing on multi-disciplinary, social, or foundational scholarly concepts]
"""

RESEARCHER_PROMPT = """
You are a professional Senior Research Intelligence Analyst. Your task is to deeply analyze raw search results gathered for the topic: "{topic}" and extract the most important, specific, and technically detailed factual information.

Here is the raw data gathered from multiple web sources, academic papers, and databases:

========================================
WEB SEARCH RESULTS:
{web_results}

========================================
WIKIPEDIA:
{wiki_results}

========================================
ACADEMIC PAPERS (arXiv):
{arxiv_results}

========================================
NEWS ARTICLES (RSS):
{news_results}

========================================
BIOMEDICAL PAPERS (PubMed):
{pubmed_results}

========================================
ACADEMIC PAPERS (OpenAlex):
{openalex_results}
========================================

Perform the following:
1. Extract 15-20 highly distinct, technically precise, and deeply informative factual items.
2. Prioritize: specific numbers, named systems/algorithms/frameworks/organizations, dates, percentages, benchmarks, research findings, and technical specifications.
3. For each fact, include the source type it came from.
4. Avoid vague generalities. Every fact must be specific enough to be cited in a research report.
5. Do NOT repeat similar facts — each item must introduce unique information.

Format STRICTLY as:
FACT: [Precise, technically detailed factual statement with numbers/names/specifics where available]
SOURCE: [web/wikipedia/arxiv/news/pubmed/openalex]
RELEVANCE: [Why this fact is critical and what unique angle it contributes]
---
"""

def researcher_agent(state: ResearchState) -> ResearchState:
    """
    Agent 1: Gathers raw information from multiple free sources.
    Skipped automatically if ChromaDB cache already loaded sources.
    Uses tier='fast' model — speed over depth for data collection.
    """
    _t0 = time.time()

    # Skip if cache already loaded sources (from cache_check_node)
    if state.get("cached_from_db") and state.get("raw_sources"):
        print("[Researcher] Cache hit detected — skipping live search.")
        return state

    topic    = state.get("topic", "")
    llm_type = state.get("llm_type", "ollama")
    llm_name = state.get("llm_name")   # None = auto-select based on tier

    print(f"[Researcher] Gathering sources for '{topic}'...")

    # Step 1: Query Expansion / Optimization using LLM
    llm = get_llm(model_type=llm_type, model_name=llm_name, tier="fast")
    
    try:
        print("[Researcher] Optimizing queries for Wikipedia, ArXiv, RSS, and Web search...")
        expansion_prompt = QUERY_EXPANSION_PROMPT.format(topic=topic)
        expansion_response = llm.invoke([HumanMessage(content=expansion_prompt)])
        expansion_text = expansion_response.content if hasattr(expansion_response, "content") else str(expansion_response)
        
        # Parse query overrides
        wiki_query = topic
        arxiv_query = topic
        web_query = f"{topic} 2026"
        news_query = topic.split()[0] if topic.split() else topic
        pubmed_query = topic
        openalex_query = topic
        
        for line in expansion_text.split("\n"):
            line = line.strip()
            if line.startswith("WIKI_QUERY:"):
                wiki_query = line.replace("WIKI_QUERY:", "").strip()
            elif line.startswith("ARXIV_QUERY:"):
                arxiv_query = line.replace("ARXIV_QUERY:", "").strip()
            elif line.startswith("WEB_QUERY:"):
                web_query = line.replace("WEB_QUERY:", "").strip()
            elif line.startswith("NEWS_QUERY:"):
                news_query = line.replace("NEWS_QUERY:", "").strip()
            elif line.startswith("PUBMED_QUERY:"):
                pubmed_query = line.replace("PUBMED_QUERY:", "").strip()
            elif line.startswith("OPENALEX_QUERY:"):
                openalex_query = line.replace("OPENALEX_QUERY:", "").strip()
                
        print(f"[Researcher] Expanded Queries formulated:")
        print(f" - Web:      '{web_query}'")
        print(f" - Wiki:     '{wiki_query}'")
        print(f" - ArXiv:    '{arxiv_query}'")
        print(f" - RSS:      '{news_query}'")
        print(f" - PubMed:   '{pubmed_query}'")
        print(f" - OpenAlex: '{openalex_query}'")
    except Exception as e:
        print(f"[Researcher] Query expansion failed ({e}). Using raw topic as fallback.")
        wiki_query = topic
        arxiv_query = topic
        web_query = f"{topic} 2026"
        news_query = topic
        pubmed_query = topic
        openalex_query = topic

    # Step 2: Gather data from all free sources using optimized queries
    web_results   = web_search(web_query)
    wiki_results  = wikipedia_search(wiki_query)
    arxiv_results = arxiv_search(arxiv_query)
    news_results  = rss_news_search(news_query)
    pubmed_results = pubmed_search(pubmed_query)
    openalex_results = openalex_search(openalex_query)

    # Format content for prompt — include deep sections when available
    web_text  = "\n\n".join([f"Source: {s['url']}\nContent: {s['content']}" for s in web_results])   if web_results   else "No general web results found."
    wiki_text = "\n\n".join([f"Source: {s['url']}\nContent: {s['content']}" for s in wiki_results])  if wiki_results  else "No Wikipedia results found."
    news_text = "\n\n".join([f"Title: {s['title']}\nContent: {s['content']}" for s in news_results])  if news_results  else "No recent news matching keywords found."
    pubmed_text = "\n\n".join([f"Paper: {s['title']}\nURL: {s['url']}\nAbstract: {s['content']}" for s in pubmed_results]) if pubmed_results else "No biomedical papers found."
    openalex_text = "\n\n".join([f"Paper: {s['title']}\nURL: {s['url']}\nAbstract: {s['content']}" for s in openalex_results]) if openalex_results else "No multi-disciplinary academic papers found."

    # Build ArXiv text with deep sections if available (Phase 2: ArXiv Deep Mode)
    if arxiv_results:
        arxiv_parts = []
        try:
            from tools.arxiv_deep import format_deep_sections_for_prompt
            for source in arxiv_results:
                if source.get("deep_sections", {}).get("deep_available"):
                    arxiv_parts.append(format_deep_sections_for_prompt(source))
                else:
                    arxiv_parts.append(f"Paper: {source['title']}\nURL: {source['url']}\nAbstract: {source['content']}")
        except Exception:
            arxiv_parts = [f"Paper: {s['title']}\nURL: {s['url']}\nAbstract: {s['content']}" for s in arxiv_results]
        arxiv_text = "\n\n".join(arxiv_parts)
    else:
        arxiv_text = "No academic papers found."


    prompt_text = RESEARCHER_PROMPT.format(
        topic=topic,
        web_results=web_text,
        wiki_results=wiki_text,
        arxiv_results=arxiv_text,
        news_results=news_text,
        pubmed_results=pubmed_text,
        openalex_results=openalex_text
    )

    # Step 3: Extract factual items using LLM
    response = llm.invoke([HumanMessage(content=prompt_text)])
    response_text = response.content if hasattr(response, "content") else str(response)

    # Combine all raw source structures to pass down
    all_sources = web_results + wiki_results + arxiv_results + news_results + pubmed_results + openalex_results
    state["raw_sources"] = all_sources

    # Store researcher's LLM notes in state — used by writer for additional context
    state["researcher_notes"] = response_text

    # Record timing
    elapsed = round(time.time() - _t0, 2)
    timings = state.get("agent_timings") or {}
    timings["researcher"] = elapsed
    state["agent_timings"] = timings

    print(f"[Researcher] Gathered {len(all_sources)} raw sources ({len(web_results)} web, {len(wiki_results)} wiki, {len(arxiv_results)} arxiv, {len(news_results)} news, {len(pubmed_results)} pubmed, {len(openalex_results)} openalex) in {elapsed}s.")
    return state
