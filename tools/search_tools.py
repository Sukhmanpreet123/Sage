"""
tools/search_tools.py
---------------------
2026 Production Edition: Light, self-contained, high-reliability search tools.

Upgraded to bypass fragile third-party LangChain wrappers:
  1. Web Search: Direct call to modernized `ddgs` package (resolves LangChain DDG import error).
  2. Wikipedia: Direct REST API query with full article extracts via urllib.
  3. ArXiv: Direct XML query via `urllib` & `ElementTree` (resolves community SDK version mismatch).
  4. News RSS: Native parsing via `feedparser` — extended feed list.
"""

import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import feedparser
import re
import time
from ddgs import DDGS

# ── Credibility Scoring ───────────────────────────────────────────────────────
# Scores reflect trustworthiness of source type and domain.
# These weights are used by the Fact Checker to adjust confidence scores.

SOURCE_TYPE_CREDIBILITY = {
    "arxiv":     95,   # Peer-reviewed academic preprints
    "pubmed":    96,   # Highly verified biomedical research
    "openalex":  92,   # Global scholarly index (academic works)
    "wikipedia": 82,   # Community-edited but highly cross-referenced
    "news":      68,   # Reputable news outlets but opinion-prone
    "web":       58,   # General web — variable quality
}

HIGH_AUTHORITY_DOMAINS = [
    ".gov", ".edu", ".ac.uk", ".ac.in", "nature.com", "science.org",
    "pubmed.ncbi.nlm.nih.gov", "ieee.org", "acm.org", "springer.com",
    "sciencedirect.com", "who.int", "nih.gov", "cdc.gov",
    "mit.edu", "stanford.edu", "oxford.ac.uk", "harvard.edu",
]

REPUTABLE_NEWS_DOMAINS = [
    "bbc.com", "reuters.com", "apnews.com", "nytimes.com", "theguardian.com",
    "techcrunch.com", "wired.com", "theverge.com", "arstechnica.com",
    "scientificamerican.com", "newscientist.com",
]


def credibility_score(url: str, source_type: str) -> int:
    """
    Calculate a credibility score (0-100) for a source based on:
    - Source type (arxiv > wikipedia > news > web)
    - Domain authority (academic/government domains get bonus)
    - Reputable news domain bonus

    Args:
        url: The source URL string
        source_type: "arxiv" | "wikipedia" | "news" | "web"

    Returns:
        Integer credibility score 0-100.
    """
    base = SOURCE_TYPE_CREDIBILITY.get(source_type, 55)
    url_lower = url.lower()

    # Academic / government domain bonus (+10)
    if any(domain in url_lower for domain in HIGH_AUTHORITY_DOMAINS):
        base = min(100, base + 10)

    # Reputable news outlet bonus (+8)
    elif source_type == "news" and any(domain in url_lower for domain in REPUTABLE_NEWS_DOMAINS):
        base = min(100, base + 8)

    # Wikipedia always gets its base (already high)
    # ArXiv always gets its base (peer-reviewed)

    return base

def web_search(query: str, max_results: int = 8) -> list[dict]:
    """Modernized DuckDuckGo search using direct ddgs package."""
    try:
        print(f"[Search] Querying DuckDuckGo for: '{query}'...")
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        parsed_results = []
        for r in results:
            url = r.get("href", r.get("link", "https://duckduckgo.com"))
            parsed_results.append({
                "title":            r.get("title", "Web Result"),
                "content":          r.get("body", r.get("snippet", "")),
                "url":              url,
                "source_type":      "web",
                "credibility_score": credibility_score(url, "web"),
            })
        return parsed_results
    except Exception as e:
        print(f"[Search] DuckDuckGo failed: {e}")
        return []

def wikipedia_search(query: str) -> list[dict]:
    """
    Query Wikipedia REST API directly. 
    First searches for matching pages, then fetches full extract for each result.
    Returns up to 5 results with rich content (up to 2000 chars per article).
    """
    try:
        print(f"[Search] Querying Wikipedia for: '{query}'...")
        quoted_query = urllib.parse.quote(query)

        # Step 1: Search for matching article titles
        search_url = (
            f"https://en.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={quoted_query}&format=json&srlimit=5"
        )
        req = urllib.request.Request(search_url, headers={"User-Agent": "ResearchBot/2.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        search_results = data.get("query", {}).get("search", [])
        parsed_results = []

        for item in search_results[:5]:
            title = item.get("title", "Wikipedia Article")
            # Step 2: Fetch full extract for each article
            extract_url = (
                f"https://en.wikipedia.org/w/api.php"
                f"?action=query&prop=extracts&exintro=true&explaintext=true"
                f"&titles={urllib.parse.quote(title)}&format=json"
            )
            try:
                req2 = urllib.request.Request(extract_url, headers={"User-Agent": "ResearchBot/2.0"})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    ext_data = json.loads(r2.read().decode("utf-8"))
                pages = ext_data.get("query", {}).get("pages", {})
                page = next(iter(pages.values()), {})
                extract = page.get("extract", "")
                # Use first 2000 characters of the extract for rich content
                content = (extract[:2000].strip()) if extract else re.sub(r'<[^>]+>', '', item.get("snippet", "")).strip()
            except Exception:
                # Fallback to search snippet
                content = re.sub(r'<[^>]+>', '', item.get("snippet", "")).strip()

            url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"
            parsed_results.append({
                "title":            title,
                "content":          content,
                "url":              url,
                "source_type":      "wikipedia",
                "credibility_score": credibility_score(url, "wikipedia"),
            })
        return parsed_results
    except Exception as e:
        print(f"[Search] Wikipedia failed: {e}")
        return []

def arxiv_search(query: str, deep_mode: bool = True) -> list[dict]:
    """
    Query ArXiv XML API directly to avoid broken community SDK wrapper.
    Returns up to 5 papers with full abstracts.
    
    Args:
        query:     Search query string
        deep_mode: If True, deep-fetches top 2 papers for methodology/results/limitations.
                   Set to False to skip deep parsing for speed-critical runs.
    """
    try:
        print(f"[Search] Querying ArXiv for: '{query}'...")
        quoted_query = urllib.parse.quote(query)
        url = f"http://export.arxiv.org/api/query?search_query=all:{quoted_query}&start=0&max_results=5"
        
        req = urllib.request.Request(url, headers={"User-Agent": "ResearchBot/2.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        parsed_results = []
        
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            title   = entry.find("{http://www.w3.org/2005/Atom}title")
            summary = entry.find("{http://www.w3.org/2005/Atom}summary")
            doc_id  = entry.find("{http://www.w3.org/2005/Atom}id")

            # Collect authors
            authors = []
            for author in entry.findall("{http://www.w3.org/2005/Atom}author"):
                name_el = author.find("{http://www.w3.org/2005/Atom}name")
                if name_el is not None:
                    authors.append(name_el.text.strip())
            author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")

            title_text   = title.text.strip().replace("\n", " ")   if title   is not None else "ArXiv Paper"
            summary_text = summary.text.strip().replace("\n", " ") if summary is not None else ""
            url_text = doc_id.text.strip() if doc_id is not None else "https://arxiv.org"
            content  = f"Authors: {author_str}\n{summary_text}" if author_str else summary_text

            parsed_results.append({
                "title":            title_text,
                "content":          content,
                "url":              url_text,
                "source_type":      "arxiv",
                "credibility_score": credibility_score(url_text, "arxiv"),
            })

        # Phase 2: Deep-fetch section content for top papers
        if deep_mode and parsed_results:
            try:
                from tools.arxiv_deep import deep_fetch_top_papers
                parsed_results = deep_fetch_top_papers(parsed_results, max_papers=2)
                print(f"[Search] ArXiv deep mode: enriched top 2 papers with full section data.")
            except Exception as e:
                print(f"[Search] ArXiv deep mode skipped: {e}")

        return parsed_results
    except Exception as e:
        print(f"[Search] ArXiv failed: {e}")
        return []

def rss_news_search(topic: str) -> list[dict]:
    """
    Free RSS feeds from major news sources.
    Extended to include Wired, Reuters, MIT Tech Review, and The Verge.
    """
    feeds = [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://feeds.reuters.com/reuters/technologyNews",
        "https://www.theverge.com/rss/index.xml",
    ]
    results = []
    keywords = topic.lower().split()

    print(f"[Search] Checking News RSS for: '{topic}'...")
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                title   = entry.get("title", "").lower()
                summary = entry.get("summary", "").lower()
                if any(kw in title or kw in summary for kw in keywords):
                    entry_url = entry.get("link", "https://news.google.com")
                    results.append({
                        "title":            entry.get("title", "News Article"),
                        "content":          entry.get("summary", entry.get("title", "")),
                        "url":              entry_url,
                        "source_type":      "news",
                        "credibility_score": credibility_score(entry_url, "news"),
                    })
        except Exception as e:
            print(f"[Search] RSS Feed parse failed for {feed_url}: {e}")
            continue

    return results[:8]  # Return top 8 relevant news items


def openalex_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Query OpenAlex API directly.
    Provides free multi-disciplinary coverage across 250M+ papers.
    Uses polite mailto parameter in user agent.
    Reconstructs abstracts from OpenAlex's inverted index representation.
    """
    try:
        print(f"[Search] Querying OpenAlex for: '{query}'...")
        quoted_query = urllib.parse.quote(query)
        url = f"https://api.openalex.org/works?search={quoted_query}&per-page={max_results}"
        
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Sage/1.0 (mailto:agent@sage.edu)"}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
            
        results = data.get("results", [])
        parsed_results = []
        
        def _reconstruct_abstract(inverted_index: dict) -> str:
            if not inverted_index:
                return ""
            word_positions = {}
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions[pos] = word
            sorted_words = [word_positions[pos] for pos in sorted(word_positions.keys())]
            return " ".join(sorted_words)

        for item in results:
            title = item.get("title") or "OpenAlex Scholarly Work"
            
            authorships = item.get("authorships", [])
            authors = [a.get("author", {}).get("display_name", "") for a in authorships if a.get("author")]
            authors = [name for name in authors if name]
            author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            
            abstract_idx = item.get("abstract_inverted_index")
            abstract_text = _reconstruct_abstract(abstract_idx) if abstract_idx else ""
            if not abstract_text:
                abstract_text = str(item.get("publication_year", ""))
                
            content = f"Authors: {author_str}\nAbstract: {abstract_text}" if author_str else abstract_text
            
            url_text = item.get("doi")
            if not url_text:
                primary_loc = item.get("primary_location") or {}
                url_text = primary_loc.get("landing_page_url") or primary_loc.get("pdf_url") or item.get("id", "https://openalex.org")
                
            parsed_results.append({
                "title":            title,
                "content":          content,
                "url":              url_text,
                "source_type":      "openalex",
                "credibility_score": credibility_score(url_text, "openalex"),
            })
        return parsed_results
    except Exception as e:
        print(f"[Search] OpenAlex failed: {e}")
        return []


def pubmed_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Query Europe PMC (PubMed) API directly for biomedical and life sciences papers.
    Returns highly verified medical and clinical literature.
    """
    try:
        print(f"[Search] Querying Europe PMC (PubMed) for: '{query}'...")
        quoted_query = urllib.parse.quote(query)
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={quoted_query}&format=json&pageSize={max_results}"
        
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Sage/1.0 (mailto:agent@sage.edu)"}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
            
        results = data.get("resultList", {}).get("result", [])
        parsed_results = []
        
        for item in results:
            title = item.get("title") or "Biomedical Research Paper"
            author_str = item.get("authorString") or ""
            abstract_text = item.get("abstractText") or item.get("snippet") or ""
            
            content = f"Authors: {author_str}\nAbstract: {abstract_text}" if author_str else abstract_text
            
            doi = item.get("doi")
            pmid = item.get("id")
            pmcid = item.get("pmcid")
            
            if doi:
                url_text = f"https://doi.org/{doi}"
            elif pmcid:
                url_text = f"https://europepmc.org/article/PMC/{pmcid}"
            elif pmid:
                url_text = f"https://europepmc.org/article/MED/{pmid}"
            else:
                url_text = "https://europepmc.org"
                
            parsed_results.append({
                "title":            title,
                "content":          content,
                "url":              url_text,
                "source_type":      "pubmed",
                "credibility_score": credibility_score(url_text, "pubmed"),
            })
        return parsed_results
    except Exception as e:
        print(f"[Search] Europe PMC failed: {e}")
        return []
