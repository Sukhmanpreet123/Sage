"""
tests/test_researcher.py
------------------------
Unit tests for the Researcher agent.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch, MagicMock


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_state(topic: str = "artificial intelligence", **kwargs) -> dict:
    """Returns a minimal ResearchState for testing."""
    return {
        "topic":           topic,
        "llm_type":        "ollama",
        "llm_name":        None,
        "raw_sources":     [],
        "cached_from_db":  False,
        "verified_claims": [],
        "human_approved":  True,
        "hitl_feedback":   "",
        "insights":        [],
        "report_draft":    "",
        "quality_score":   0,
        "critic_feedback": "",
        "iterations":      0,
        "pdf_path":        "",
        "error":           None,
        **kwargs
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestResearcherAgent:

    @patch("agents.researcher.web_search")
    @patch("agents.researcher.wikipedia_search")
    @patch("agents.researcher.arxiv_search")
    @patch("agents.researcher.rss_news_search")
    @patch("agents.researcher.pubmed_search")
    @patch("agents.researcher.openalex_search")
    @patch("agents.researcher.get_llm")
    def test_researcher_returns_raw_sources(
        self, mock_llm, mock_openalex, mock_pubmed, mock_rss, mock_arxiv, mock_wiki, mock_web
    ):
        """Researcher should populate raw_sources from all search tools."""
        # Arrange
        mock_web.return_value   = [{"title": "Web",  "content": "AI news",  "url": "web.com",  "source_type": "web"}]
        mock_wiki.return_value  = [{"title": "Wiki", "content": "AI wiki",  "url": "wiki.org", "source_type": "wikipedia"}]
        mock_arxiv.return_value = [{"title": "ArXiv","content": "AI paper", "url": "arxiv.org","source_type": "arxiv"}]
        mock_rss.return_value   = [{"title": "News", "content": "AI news",  "url": "news.com", "source_type": "news"}]
        mock_pubmed.return_value = [{"title": "PubMed", "content": "Medical", "url": "pubmed.org", "source_type": "pubmed"}]
        mock_openalex.return_value = [{"title": "OpenAlex", "content": "Scholarly", "url": "openalex.org", "source_type": "openalex"}]

        mock_response = MagicMock()
        mock_response.content = "Structured research output"
        mock_llm.return_value.invoke.return_value = mock_response

        state = make_state()

        # Act
        from agents.researcher import researcher_agent
        result = researcher_agent(state)

        # Assert
        assert len(result["raw_sources"]) == 6
        source_types = [s["source_type"] for s in result["raw_sources"]]
        assert "web"       in source_types
        assert "wikipedia" in source_types
        assert "arxiv"     in source_types
        assert "news"      in source_types
        assert "pubmed"    in source_types
        assert "openalex"  in source_types

    @patch("agents.researcher.web_search")
    @patch("agents.researcher.wikipedia_search")
    @patch("agents.researcher.arxiv_search")
    @patch("agents.researcher.rss_news_search")
    @patch("agents.researcher.pubmed_search")
    @patch("agents.researcher.openalex_search")
    @patch("agents.researcher.get_llm")
    def test_researcher_skips_when_cached(
        self, mock_llm, mock_openalex, mock_pubmed, mock_rss, mock_arxiv, mock_wiki, mock_web
    ):
        """Researcher should skip all searches when cache hit detected."""
        state = make_state(
            cached_from_db=True,
            raw_sources=[{"title": "Cached", "content": "data", "url": "cache.com", "source_type": "web"}]
        )

        from agents.researcher import researcher_agent
        result = researcher_agent(state)

        # No search tools should be called
        mock_web.assert_not_called()
        mock_wiki.assert_not_called()
        mock_arxiv.assert_not_called()
        mock_rss.assert_not_called()
        mock_pubmed.assert_not_called()
        mock_openalex.assert_not_called()
        mock_llm.assert_not_called()

        assert len(result["raw_sources"]) == 1  # Cache unchanged

    @patch("agents.researcher.web_search", return_value=[])
    @patch("agents.researcher.wikipedia_search", return_value=[])
    @patch("agents.researcher.arxiv_search", return_value=[])
    @patch("agents.researcher.rss_news_search", return_value=[])
    @patch("agents.researcher.pubmed_search", return_value=[])
    @patch("agents.researcher.openalex_search", return_value=[])
    @patch("agents.researcher.get_llm")
    def test_researcher_handles_empty_search_results(
        self, mock_llm, *args
    ):
        """Researcher should handle case where all searches return nothing."""
        mock_response = MagicMock()
        mock_response.content = ""
        mock_llm.return_value.invoke.return_value = mock_response

        state = make_state()

        from agents.researcher import researcher_agent
        result = researcher_agent(state)

        assert isinstance(result["raw_sources"], list)
        assert len(result["raw_sources"]) == 0
