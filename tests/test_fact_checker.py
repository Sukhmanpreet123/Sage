"""
tests/test_fact_checker.py
--------------------------
Unit tests for the Fact Checker agent.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch, MagicMock

from agents.fact_checker import parse_verification_output


def make_state(raw_sources=None, **kwargs) -> dict:
    return {
        "topic":           "machine learning",
        "llm_type":        "ollama",
        "llm_name":        None,
        "raw_sources":     raw_sources or [],
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


MOCK_SOURCES = [
    {"title": "Source A", "content": "ML models improve with more data.", "url": "a.com", "source_type": "web"},
    {"title": "Source B", "content": "ML models improve with more data.", "url": "b.org", "source_type": "wikipedia"},
    {"title": "Source C", "content": "Deep learning is a subset of ML.",  "url": "c.edu", "source_type": "arxiv"},
]


class TestParseVerificationOutput:

    def test_parses_verified_claim(self):
        """Parser should correctly extract a VERIFIED claim."""
        text = """
CLAIM: Machine learning models improve with more data.
STATUS: VERIFIED
CONFIDENCE: 92
REASONING: Multiple sources agree on this.
---
"""
        claims = parse_verification_output(text)
        assert len(claims) == 1
        assert claims[0]["claim"] == "Machine learning models improve with more data."
        assert claims[0]["status"] == "VERIFIED"
        assert claims[0]["confidence"] == 92

    def test_parses_multiple_claims(self):
        """Parser should handle multiple claims separated by ---."""
        text = """
CLAIM: Claim one.
STATUS: VERIFIED
CONFIDENCE: 90
REASONING: Good sources.
---
CLAIM: Claim two.
STATUS: UNCERTAIN
CONFIDENCE: 50
REASONING: Only one source.
---
"""
        claims = parse_verification_output(text)
        assert len(claims) == 2
        assert claims[0]["status"] == "VERIFIED"
        assert claims[1]["status"] == "UNCERTAIN"

    def test_handles_malformed_output(self):
        """Parser should not crash on empty or malformed LLM output."""
        claims = parse_verification_output("")
        assert claims == []

        claims = parse_verification_output("No structured output here.")
        assert claims == []


class TestFactCheckerAgent:

    @patch("agents.fact_checker.get_llm")
    def test_only_verified_claims_pass(self, mock_llm):
        """Only VERIFIED claims should remain in state after fact checking."""
        mock_response = MagicMock()
        mock_response.content = """
CLAIM: ML models improve with more data.
STATUS: VERIFIED
CONFIDENCE: 90
REASONING: Two sources agree.
---
CLAIM: ML can predict the future.
STATUS: REMOVE
CONFIDENCE: 5
REASONING: Contradicted by sources.
---
"""
        mock_llm.return_value.invoke.return_value = mock_response

        state = make_state(raw_sources=MOCK_SOURCES)

        from agents.fact_checker import fact_checker_agent
        result = fact_checker_agent(state)

        assert all(c["status"] == "VERIFIED" for c in result["verified_claims"])
        assert len(result["verified_claims"]) == 1

    @patch("agents.fact_checker.get_llm")
    def test_fallback_when_no_verified_claims(self, mock_llm):
        """Agent should apply fallback if LLM produces no parseable output."""
        mock_response = MagicMock()
        mock_response.content = "I cannot verify anything."
        mock_llm.return_value.invoke.return_value = mock_response

        state = make_state(raw_sources=MOCK_SOURCES)

        from agents.fact_checker import fact_checker_agent
        result = fact_checker_agent(state)

        # Fallback should produce at least some claims
        assert len(result["verified_claims"]) > 0

    def test_empty_sources_returns_empty_claims(self):
        """If no raw sources, agent should return empty verified_claims gracefully."""
        state = make_state(raw_sources=[])

        from agents.fact_checker import fact_checker_agent
        result = fact_checker_agent(state)

        assert result["verified_claims"] == []
