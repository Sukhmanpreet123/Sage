"""
tools/arxiv_deep.py
-------------------
Phase 2 Feature: ArXiv Deep Mode

Instead of only using paper abstracts, this module:
1. Fetches the ar5iv.labs.arxiv.org HTML version of each paper (free, no API key needed)
2. Uses BeautifulSoup to extract named sections: Introduction, Methodology,
   Results/Experiments, Limitations, Conclusion
3. Returns structured dicts the Researcher agent can use to produce
   methodology-aware, limitation-aware research notes

Rate-limiting: We only deep-fetch the top 2 papers (configurable) to keep latency under 15s.
"""

import urllib.request
import urllib.parse
import re
import time

# Try to import BeautifulSoup; if not installed, degrade gracefully
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# Section name patterns to detect major paper sections
SECTION_PATTERNS = {
    "introduction": [r"introduction", r"background", r"motivation", r"overview"],
    "methodology":  [r"method", r"approach", r"algorithm", r"model", r"architecture", r"proposed", r"framework"],
    "results":      [r"result", r"experiment", r"evaluation", r"performance", r"benchmark", r"empirical"],
    "limitations":  [r"limitation", r"weakness", r"shortcoming", r"future work", r"discussion", r"constraint"],
    "conclusion":   [r"conclusion", r"summary", r"takeaway", r"closing"],
}

MAX_SECTION_CHARS = 1200  # Max characters per section to keep prompt size manageable


def _arxiv_id_from_url(arxiv_url: str) -> str:
    """
    Extracts the ArXiv paper ID from a full arXiv URL.
    Example: 'https://arxiv.org/abs/2301.07041' -> '2301.07041'
    """
    # Handle various URL formats
    match = re.search(r"arxiv\.org/(?:abs|pdf|html)/([0-9]+\.[0-9]+(?:v\d+)?)", arxiv_url)
    if match:
        return match.group(1)
    # Also handle plain IDs
    plain = re.search(r"([0-9]{4}\.[0-9]{4,5})", arxiv_url)
    if plain:
        return plain.group(1)
    return ""


def _fetch_html(url: str, timeout: int = 15) -> str:
    """Fetches raw HTML from a URL with a descriptive User-Agent."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 Sage-ResearchBot/2.0 (Academic; +https://github.com)"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[ArXivDeep] HTTP fetch failed for {url}: {e}")
        return ""


def _match_section_type(heading_text: str) -> str:
    """Classify a section heading into one of our canonical section types."""
    heading_lower = heading_text.lower()
    for section_type, patterns in SECTION_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, heading_lower):
                return section_type
    return "other"


def _extract_sections_from_html(html: str) -> dict:
    """
    Uses BeautifulSoup to parse the ar5iv HTML and extract named sections.
    Returns a dict: {section_type: extracted_text}
    """
    if not BS4_AVAILABLE:
        return {}

    soup = BeautifulSoup(html, "lxml")

    # ar5iv uses <section> or <div class="ltx_section"> tags
    # Standard headings are h2/h3/h4 inside these sections
    sections_found = {
        "introduction": "",
        "methodology":  "",
        "results":      "",
        "limitations":  "",
        "conclusion":   "",
    }

    # Try to find all section-like heading elements
    heading_tags = soup.find_all(["h1", "h2", "h3", "h4"], limit=50)

    for tag in heading_tags:
        heading_text = tag.get_text(separator=" ", strip=True)
        section_type = _match_section_type(heading_text)

        if section_type == "other":
            continue

        # Collect text from siblings or parent section until next heading
        text_parts = []
        for sibling in tag.find_next_siblings():
            if sibling.name in ["h1", "h2", "h3", "h4"]:
                break  # Stop at next section
            text = sibling.get_text(separator=" ", strip=True)
            if text:
                text_parts.append(text)
            if len(" ".join(text_parts)) > MAX_SECTION_CHARS:
                break

        section_text = " ".join(text_parts)[:MAX_SECTION_CHARS].strip()

        # Only keep the first instance of each section type
        if section_text and not sections_found[section_type]:
            sections_found[section_type] = section_text

    return {k: v for k, v in sections_found.items() if v}


def fetch_arxiv_paper_sections(arxiv_url: str, paper_title: str = "") -> dict:
    """
    Main function: fetch and extract deep sections from an ArXiv paper.

    Args:
        arxiv_url:   The arXiv.org URL (abs or pdf format)
        paper_title: Display title for logging

    Returns:
        dict with keys: title, url, abstract, introduction, methodology,
                        results, limitations, conclusion, deep_available
    """
    result = {
        "title":         paper_title or arxiv_url,
        "url":           arxiv_url,
        "abstract":      "",
        "introduction":  "",
        "methodology":   "",
        "results":       "",
        "limitations":   "",
        "conclusion":    "",
        "deep_available": False,
    }

    if not BS4_AVAILABLE:
        print("[ArXivDeep] BeautifulSoup4 not installed. Skipping deep parse. Run: pip install beautifulsoup4 lxml")
        return result

    paper_id = _arxiv_id_from_url(arxiv_url)
    if not paper_id:
        print(f"[ArXivDeep] Could not extract paper ID from URL: {arxiv_url}")
        return result

    # ar5iv provides rendered HTML versions of ArXiv papers (free, no auth)
    ar5iv_url = f"https://ar5iv.labs.arxiv.org/html/{paper_id}"
    print(f"[ArXivDeep] Fetching HTML version: {ar5iv_url}")

    html = _fetch_html(ar5iv_url)
    if not html or len(html) < 1000:
        # Fallback: try the arxiv HTML export endpoint
        arxiv_html_url = f"https://arxiv.org/html/{paper_id}"
        print(f"[ArXivDeep] ar5iv failed. Trying: {arxiv_html_url}")
        html = _fetch_html(arxiv_html_url)

    if not html or len(html) < 500:
        print(f"[ArXivDeep] Could not fetch HTML for paper {paper_id}")
        return result

    # Extract the abstract specifically
    try:
        soup = BeautifulSoup(html, "lxml")
        abstract_el = soup.find("div", class_=re.compile(r"abstract|ltx_abstract", re.I))
        if abstract_el:
            result["abstract"] = abstract_el.get_text(separator=" ", strip=True)[:1000]
    except Exception:
        pass

    # Extract all named sections
    sections = _extract_sections_from_html(html)
    result.update(sections)
    result["deep_available"] = bool(sections)

    filled = [k for k in ["introduction", "methodology", "results", "limitations", "conclusion"] if result.get(k)]
    print(f"[ArXivDeep] Extracted {len(filled)} sections: {filled}")
    return result


def deep_fetch_top_papers(arxiv_sources: list, max_papers: int = 2) -> list:
    """
    Takes a list of source dicts from arxiv_search() and deep-fetches the top N.
    Attaches 'deep_sections' key to each source dict in place.

    Args:
        arxiv_sources: List of source dicts from search_tools.arxiv_search()
        max_papers: Maximum number of papers to deep-fetch (default: 2 for speed)

    Returns:
        List of source dicts with 'deep_sections' key added to eligible papers.
    """
    enriched = []
    fetch_count = 0

    for source in arxiv_sources:
        if fetch_count >= max_papers:
            source["deep_sections"] = {}
            enriched.append(source)
            continue

        url   = source.get("url", "")
        title = source.get("title", "")

        if "arxiv.org" in url.lower() or re.search(r"\d{4}\.\d{4}", url):
            print(f"[ArXivDeep] Deep-fetching: {title[:60]}...")
            sections = fetch_arxiv_paper_sections(url, title)
            source["deep_sections"] = sections
            fetch_count += 1
            time.sleep(0.5)  # Polite delay between requests
        else:
            source["deep_sections"] = {}

        enriched.append(source)

    return enriched


def format_deep_sections_for_prompt(source: dict) -> str:
    """
    Formats a source dict's deep_sections into a readable block for LLM prompts.
    Returns a multi-line string showing all available deep sections.
    """
    sections = source.get("deep_sections", {})
    if not sections or not sections.get("deep_available"):
        return f"  [Abstract only] {source.get('content', '')[:500]}"

    title = source.get("title", "Unknown Paper")
    lines = [f"\n  📑 DEEP ANALYSIS: {title}"]

    section_labels = {
        "abstract":     "Abstract",
        "introduction": "Introduction / Background",
        "methodology":  "Methodology / Approach",
        "results":      "Results / Experiments",
        "limitations":  "Limitations / Future Work",
        "conclusion":   "Conclusion",
    }

    for key, label in section_labels.items():
        text = sections.get(key, "")
        if text:
            lines.append(f"\n  [{label}]\n  {text[:600]}")

    return "\n".join(lines)
