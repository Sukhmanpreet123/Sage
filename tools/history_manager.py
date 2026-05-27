"""
tools/history_manager.py
------------------------
Manages persistent run history for the Research Intelligence System.
Saves run metadata to output/history.json after each successful research run.
Enables the History Dashboard in the Streamlit sidebar.
"""

import json
import os
from datetime import datetime
from typing import Optional

HISTORY_FILE = os.path.join("output", "history.json")

def _ensure_output_dir():
    os.makedirs("output", exist_ok=True)

def save_run(
    topic: str,
    quality_score: int,
    verified_count: int,
    source_count: int,
    llm_type: str,
    iterations: int,
    pdf_path: str,
    cached: bool,
    agent_timings: Optional[dict] = None
) -> None:
    """Save a completed research run to history."""
    _ensure_output_dir()

    history = load_history()
    entry = {
        "id":             f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "topic":          topic,
        "timestamp":      datetime.now().isoformat(),
        "date_display":   datetime.now().strftime("%b %d, %Y %H:%M"),
        "quality_score":  quality_score,
        "verified_count": verified_count,
        "source_count":   source_count,
        "llm_type":       llm_type,
        "iterations":     iterations,
        "pdf_path":       pdf_path,
        "cached":         cached,
        "agent_timings":  agent_timings or {},
    }

    # Prepend newest run at the top, keep last 20 runs
    history.insert(0, entry)
    history = history[:20]

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[History] Failed to save run: {e}")


def load_history() -> list:
    """Load all previous runs from history file."""
    _ensure_output_dir()
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def delete_run(run_id: str) -> None:
    """Delete a specific run from history by ID."""
    history = load_history()
    history = [r for r in history if r.get("id") != run_id]
    _ensure_output_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def clear_history() -> None:
    """Delete all run history."""
    _ensure_output_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
