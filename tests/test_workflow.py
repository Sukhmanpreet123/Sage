"""
tests/test_workflow.py
----------------------
Integration-level tests for the LangGraph workflow.
Tests graph compilation, state initialization, and routing logic.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch

from graph.workflow import make_initial_state
from graph.state import ResearchState
from agents.critic import should_rewrite, parse_critic_score, extract_feedback


# ── State Helper Tests ────────────────────────────────────────────────────────

class TestMakeInitialState:

    def test_all_required_keys_present(self):
        """make_initial_state should produce a complete ResearchState."""
        state = make_initial_state("Quantum computing 2026")

        required_keys = [
            "topic", "llm_type", "llm_name",
            "raw_sources", "cached_from_db",
            "verified_claims", "human_approved", "hitl_feedback",
            "insights", "report_draft",
            "quality_score", "critic_feedback",
            "iterations", "pdf_path", "error", "thread_id"
        ]
        for key in required_keys:
            assert key in state, f"Missing key: '{key}'"

    def test_thread_id_auto_generated(self):
        """thread_id should be auto-generated as a UUID string if not provided."""
        state = make_initial_state("test topic")
        assert isinstance(state["thread_id"], str)
        assert len(state["thread_id"]) == 36  # UUID4 format

    def test_custom_thread_id(self):
        """User-provided thread_id should be preserved."""
        state = make_initial_state("test topic", thread_id="my-custom-run-001")
        assert state["thread_id"] == "my-custom-run-001"

    def test_human_approved_default_false(self):
        """human_approved should default to False (require HITL)."""
        state = make_initial_state("test topic")
        assert state["human_approved"] is False

    def test_human_approved_can_be_overridden(self):
        """human_approved=True should skip HITL (batch mode)."""
        state = make_initial_state("test topic", human_approved=True)
        assert state["human_approved"] is True


# ── Critic Routing Tests ──────────────────────────────────────────────────────

class TestCriticRouting:

    def test_should_pass_when_score_ge_70(self):
        """Score >= 70 should route to pdf_gen."""
        state = make_initial_state("test")
        state["quality_score"] = 75
        state["iterations"]    = 1
        assert should_rewrite(state) == "pdf_gen"

    def test_should_rewrite_when_score_lt_70_and_iterations_lt_3(self):
        """Score < 70 AND iterations < 3 should route back to writer."""
        state = make_initial_state("test")
        state["quality_score"] = 60
        state["iterations"]    = 1
        assert should_rewrite(state) == "writer"

    def test_should_pass_when_max_iterations_reached(self):
        """Even with score < 70, route to pdf_gen if iterations >= 3."""
        state = make_initial_state("test")
        state["quality_score"] = 55
        state["iterations"]    = 3
        assert should_rewrite(state) == "pdf_gen"

    def test_edge_score_exactly_70_passes(self):
        """Score of exactly 70 should PASS."""
        state = make_initial_state("test")
        state["quality_score"] = 70
        state["iterations"]    = 1
        assert should_rewrite(state) == "pdf_gen"


# ── Critic Parser Tests ───────────────────────────────────────────────────────

class TestCriticParsers:

    def test_parse_critic_score_valid(self):
        text = "ACCURACY_SCORE: 80\nCOMPLETENESS_SCORE: 75\nCLARITY_SCORE: 70\nWEIGHTED_TOTAL: 75.5\nDECISION: PASS\nFEEDBACK: Good report."
        assert parse_critic_score(text) == 75

    def test_parse_critic_score_fallback(self):
        """Falls back to 75 if WEIGHTED_TOTAL not found."""
        assert parse_critic_score("No score here.") == 75

    def test_extract_feedback(self):
        text = "ACCURACY_SCORE: 60\nWEIGHTED_TOTAL: 63\nDECISION: REWRITE\nFEEDBACK: Add more statistics and improve clarity."
        feedback = extract_feedback(text)
        assert "statistics" in feedback.lower()

    def test_extract_feedback_fallback(self):
        """Returns default message if FEEDBACK not found."""
        feedback = extract_feedback("No feedback here.")
        assert isinstance(feedback, str)
        assert len(feedback) > 0


# ── Graph Compilation Test ────────────────────────────────────────────────────

class TestGraphCompilation:

    def test_graph_compiles_without_error(self):
        """build_research_graph should compile without raising exceptions."""
        from graph.workflow import build_research_graph
        graph = build_research_graph(use_checkpointer=False)
        assert graph is not None

    def test_graph_has_correct_nodes(self):
        """Compiled graph should contain all expected nodes."""
        from graph.workflow import build_research_graph
        graph = build_research_graph(use_checkpointer=False)
        node_names = list(graph.nodes.keys())
        expected = ["cache_check", "researcher", "fact_checker",
                    "human_review", "analyst", "writer", "critic", "pdf_gen"]
        for node in expected:
            assert node in node_names, f"Missing node: '{node}'"
