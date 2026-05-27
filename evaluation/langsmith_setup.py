"""
evaluation/langsmith_setup.py
-----------------------------
LangSmith observability configuration for the Research Intelligence System.

LangSmith provides full tracing of every LLM call and every node transition
in the LangGraph workflow — essential for debugging agent loops.

Setup:
  1. Get a free key at https://smith.langchain.com
  2. Add LANGCHAIN_API_KEY to your .env file
  3. This module auto-configures tracing on import.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def setup_langsmith(project_name: str = "research-intelligence-system") -> bool:
    """
    Configures LangSmith tracing environment variables.

    Returns True if successfully configured, False if API key is missing.
    """

    api_key = os.getenv("LANGCHAIN_API_KEY")

    if not api_key:
        print(
            "⚠️  LangSmith: LANGCHAIN_API_KEY not found in .env. "
            "Tracing disabled. Get a free key at https://smith.langchain.com"
        )
        return False

    # Set LangSmith env vars
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"]    = project_name
    os.environ["LANGCHAIN_ENDPOINT"]   = "https://api.smith.langchain.com"

    print(f"✅ LangSmith tracing enabled → project: '{project_name}'")
    print(f"   View traces at: https://smith.langchain.com/projects/{project_name}")
    return True


def disable_langsmith():
    """Disables LangSmith tracing (e.g., for tests)."""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


# Auto-configure on import
_enabled = setup_langsmith()
