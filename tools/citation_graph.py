"""
tools/citation_graph.py
-----------------------
Phase 2 Feature: Citation Landscape Graph

Queries the Semantic Scholar Open API (completely free, no API key required)
to fetch the citation network around an ArXiv paper:
  - Papers it CITES (foundational prior art)
  - Papers that CITE it (follow-on research)

Then builds an interactive network graph using PyVis and exports it as
a self-contained HTML string for embedding in Streamlit via st.components.v1.html().

Node colors:
  - Blue (#3b82f6):  The central source paper
  - Green (#10b981): Papers that CITE this paper (citing papers / follow-on work)
  - Orange (#f97316): Papers this paper CITES (references / prior art)
"""

import urllib.request
import urllib.parse
import json
import re
import time

# Try to import networkx and pyvis
try:
    import networkx as nx
    NX_AVAILABLE = True
except ImportError:
    NX_AVAILABLE = False

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
MAX_CITATIONS_PER_DIRECTION = 15   # Max citing + cited papers each (to keep graph readable)
REQUEST_TIMEOUT = 12


def _arxiv_id_from_url(arxiv_url: str) -> str:
    """Extract the numeric ArXiv paper ID from a URL."""
    match = re.search(r"arxiv\.org/(?:abs|pdf|html)/([0-9]+\.[0-9]+(?:v\d+)?)", arxiv_url)
    if match:
        return match.group(1)
    plain = re.search(r"([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", arxiv_url)
    if plain:
        return plain.group(1)
    return ""


def _semantic_scholar_request(endpoint: str) -> dict:
    """Make a request to the Semantic Scholar API with graceful error handling."""
    url = f"{SEMANTIC_SCHOLAR_BASE}/{endpoint}"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Sage-ResearchBot/2.0 (Academic use)"}
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[CitationGraph] API request failed for {endpoint}: {e}")
        return {}


def fetch_paper_by_arxiv_id(arxiv_id: str) -> dict:
    """
    Looks up a paper on Semantic Scholar by ArXiv ID.
    Returns paper metadata including Semantic Scholar paper ID.
    """
    endpoint = f"paper/arXiv:{arxiv_id}?fields=paperId,title,year,citationCount,referenceCount,authors"
    result = _semantic_scholar_request(endpoint)
    return result


def fetch_citations(paper_id: str, limit: int = MAX_CITATIONS_PER_DIRECTION) -> list:
    """
    Fetch papers that CITE the given paper (follow-on research).
    These are rendered as green nodes.
    """
    endpoint = f"paper/{paper_id}/citations?fields=paperId,title,year,authors&limit={limit}"
    data = _semantic_scholar_request(endpoint)
    papers = []
    for item in data.get("data", []):
        citing = item.get("citingPaper", {})
        if citing.get("paperId") and citing.get("title"):
            papers.append({
                "id":     citing["paperId"],
                "title":  citing["title"][:80],
                "year":   citing.get("year", "N/A"),
                "type":   "citing",   # This paper cites the source
            })
    return papers


def fetch_references(paper_id: str, limit: int = MAX_CITATIONS_PER_DIRECTION) -> list:
    """
    Fetch papers that this paper CITES (prior art / references).
    These are rendered as orange nodes.
    """
    endpoint = f"paper/{paper_id}/references?fields=paperId,title,year,authors&limit={limit}"
    data = _semantic_scholar_request(endpoint)
    papers = []
    for item in data.get("data", []):
        cited = item.get("citedPaper", {})
        if cited.get("paperId") and cited.get("title"):
            papers.append({
                "id":     cited["paperId"],
                "title":  cited["title"][:80],
                "year":   cited.get("year", "N/A"),
                "type":   "cited",   # This paper is cited by the source
            })
    return papers


def build_citation_graph(source_paper: dict, citing_papers: list, cited_papers: list):
    """
    Builds a NetworkX directed graph from the citation data.

    Node attributes:
      - label: Paper title (truncated)
      - node_type: "source" | "citing" | "cited"
      - year: Publication year

    Edge attributes:
      - direction: "cites" | "is_cited_by"
    """
    if not NX_AVAILABLE:
        raise ImportError("networkx not installed. Run: pip install networkx")

    G = nx.DiGraph()

    source_id = source_paper.get("paperId", "source")
    source_title = source_paper.get("title", "Source Paper")[:80]

    # Add source node
    G.add_node(source_id, label=source_title, node_type="source",
               year=source_paper.get("year", "N/A"),
               citation_count=source_paper.get("citationCount", 0))

    # Add citing papers (papers that reference the source)
    for paper in citing_papers:
        G.add_node(paper["id"], label=paper["title"], node_type="citing", year=paper["year"])
        G.add_edge(paper["id"], source_id, direction="cites")

    # Add cited papers (papers the source references)
    for paper in cited_papers:
        G.add_node(paper["id"], label=paper["title"], node_type="cited", year=paper["year"])
        G.add_edge(source_id, paper["id"], direction="cites")

    return G


def render_citation_graph_html(G, title: str = "Citation Network") -> str:
    """
    Converts a NetworkX graph to an interactive PyVis HTML string.
    Color scheme:
      Blue  = source paper
      Green = papers citing this paper (follow-on)
      Orange = papers this paper cites (prior art)
    """
    if not PYVIS_AVAILABLE:
        raise ImportError("pyvis not installed. Run: pip install pyvis")

    net = Network(
        height="560px",
        width="100%",
        directed=True,
        bgcolor="#f8fafc",
        font_color="#0f172a",
        notebook=False,
    )

    node_colors = {
        "source":  "#3b82f6",   # Blue — the central paper
        "citing":  "#10b981",   # Green — cites this paper
        "cited":   "#f97316",   # Orange — cited by this paper
    }
    node_sizes = {
        "source": 35,
        "citing": 20,
        "cited":  20,
    }

    for node_id, attrs in G.nodes(data=True):
        node_type = attrs.get("node_type", "cited")
        label     = attrs.get("label", node_id[:30])
        year      = attrs.get("year", "N/A")
        tooltip   = f"{label}\nYear: {year}"
        if node_type == "source":
            citation_count = attrs.get("citation_count", 0)
            tooltip += f"\nTotal Citations: {citation_count}"

        net.add_node(
            node_id,
            label=label[:40] + ("..." if len(label) > 40 else ""),
            color=node_colors.get(node_type, "#64748b"),
            size=node_sizes.get(node_type, 20),
            title=tooltip,
            font={"size": 11, "color": "#0f172a"},
            borderWidth=2,
            borderWidthSelected=4,
        )

    for src, dst, attrs in G.edges(data=True):
        net.add_edge(src, dst, color="#94a3b8", arrows="to", width=1.5)

    # Configure physics for clean layout
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 120,
          "springConstant": 0.04
        },
        "maxVelocity": 50,
        "minVelocity": 0.1,
        "stabilization": {"iterations": 200}
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200,
        "hideEdgesOnDrag": true
      }
    }
    """)

    # Export to HTML string
    html = net.generate_html()

    # Inject legend into the HTML
    legend_html = f"""
    <div style="position:absolute; top:12px; left:12px; background:rgba(248,250,252,0.95);
                border:1px solid #e2e8f0; border-radius:10px; padding:10px 14px; font-size:12px;
                font-family:'Plus Jakarta Sans',sans-serif; z-index:1000;">
      <b style="color:#0f172a;">{title[:60]}</b><br>
      <div style="margin-top:6px;">
        <span style="display:inline-block;width:12px;height:12px;background:#3b82f6;border-radius:50%;margin-right:5px;"></span>
        <span style="color:#0f172a;">Source Paper</span>
      </div>
      <div style="margin-top:3px;">
        <span style="display:inline-block;width:12px;height:12px;background:#10b981;border-radius:50%;margin-right:5px;"></span>
        <span style="color:#0f172a;">Papers citing this</span>
      </div>
      <div style="margin-top:3px;">
        <span style="display:inline-block;width:12px;height:12px;background:#f97316;border-radius:50%;margin-right:5px;"></span>
        <span style="color:#0f172a;">Papers this cites</span>
      </div>
    </div>
    """
    # Insert legend before </body>
    html = html.replace("</body>", legend_html + "\n</body>")
    return html


def fetch_and_render_citation_graph(arxiv_url: str, paper_title: str = "") -> str:
    """
    Main entry point: given an ArXiv URL, fetches the citation network and
    returns a self-contained interactive HTML string ready for st.components.v1.html().

    Returns empty string if data cannot be fetched.
    """
    if not NX_AVAILABLE or not PYVIS_AVAILABLE:
        raise ImportError(
            "Citation graph requires networkx and pyvis.\n"
            "Run: pip install networkx pyvis"
        )

    arxiv_id = _arxiv_id_from_url(arxiv_url)
    if not arxiv_id:
        print(f"[CitationGraph] Could not extract ArXiv ID from: {arxiv_url}")
        return ""

    print(f"[CitationGraph] Looking up paper arXiv:{arxiv_id} on Semantic Scholar...")
    paper = fetch_paper_by_arxiv_id(arxiv_id)

    if not paper or not paper.get("paperId"):
        print(f"[CitationGraph] Paper not found on Semantic Scholar for arXiv:{arxiv_id}")
        return ""

    paper_id = paper["paperId"]
    display_title = paper.get("title", paper_title or arxiv_id)
    print(f"[CitationGraph] Found: '{display_title}' | Citations: {paper.get('citationCount', 0)}")

    # Fetch both directions
    time.sleep(0.3)  # Polite pause
    print("[CitationGraph] Fetching citing papers...")
    citing = fetch_citations(paper_id)

    time.sleep(0.3)
    print("[CitationGraph] Fetching cited references...")
    cited = fetch_references(paper_id)

    if not citing and not cited:
        print("[CitationGraph] No citation data found.")
        return ""

    print(f"[CitationGraph] Building graph: {len(citing)} citing | {len(cited)} cited papers.")
    G = build_citation_graph(paper, citing, cited)
    html = render_citation_graph_html(G, title=display_title)

    print(f"[CitationGraph] Graph rendered successfully ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges).")
    return html
