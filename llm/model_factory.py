"""
llm/model_factory.py
--------------------
2026 Edition: Unified ChatModel interface with auto GPU detection,
model tiering (fast vs. powerful), and updated model names.

Supported providers (all FREE):
  - ollama   → ChatOllama (Llama 4 Scout / Maverick, runs locally, auto GPU/CPU)
  - groq     → ChatGroq   (Llama 4 Scout on Groq LPU — fastest free inference)
  - gemini   → ChatGoogleGenerativeAI (Gemini 2.0 Flash — Google AI Studio free)
"""

import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

# ── Model tiering ────────────────────────────────────────────────────────────
# Use FAST models for routing / analyst (less reasoning needed)
# Use POWERFUL models for fact-checker / writer / critic (reasoning heavy)
#
# Ollama defaults:  fast="llama4:scout"  powerful="llama4:maverick"
#                   fallback (no GPU): fast="llama3.2"  powerful="mistral"
# Groq defaults:    fast="llama-4-scout-17b-16e-instruct"
#                   powerful="llama-4-maverick-17b-128e-instruct"
# Gemini defaults:  fast="gemini-2.0-flash"  powerful="gemini-2.0-flash"
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_FAST_MODEL     = os.getenv("OLLAMA_FAST_MODEL",     "llama4:scout")
OLLAMA_POWERFUL_MODEL = os.getenv("OLLAMA_POWERFUL_MODEL", "llama4:maverick")
OLLAMA_FALLBACK_FAST  = "llama3.2"
OLLAMA_FALLBACK_POWER = "mistral"

GROQ_FAST_MODEL     = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_POWERFUL_MODEL = "llama-3.3-70b-versatile"

GEMINI_MODEL = "gemini-2.0-flash"


def _detect_gpu() -> bool:
    """
    Detect whether a GPU is available for Ollama.
    Checks nvidia-smi (NVIDIA) and a basic ROCm probe.
    Falls back gracefully to CPU if detection fails.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            gpu_name = result.stdout.strip().split("\n")[0]
            print(f"[GPU] Detected: {gpu_name}. Using llama4 models.")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("[GPU] AMD GPU (ROCm) detected. Using llama4 models.")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print("[CPU] No GPU detected -- using CPU-friendly models (llama3.2 / mistral).")
    return False


def get_llm(
    model_type: str = "ollama",
    model_name: str | None = None,
    tier: str = "fast",           # "fast" or "powerful"
    temperature: float | None = None  # None = use provider default (0.1)
):
    """
    Returns a unified ChatModel (all providers return the same interface).

    Args:
        model_type: "ollama" | "groq" | "gemini"
        model_name: explicit model override (optional).
                    If None, auto-selects based on `tier` and GPU availability.
        tier:       "fast"  — for researcher / analyst (speed > depth)
                    "powerful" — for fact-checker / writer / critic (depth > speed)
        temperature: optional float override. Default 0.1 for precision;
                     pass 0.35 for writer to encourage creative depth.

    Returns:
        A LangChain ChatModel with .invoke() / .stream() interface.
    """
    # Resolve temperature: caller override wins, else default 0.1
    _temp = temperature if temperature is not None else 0.1

    # ── Ollama (local, auto GPU/CPU) ─────────────────────────────────────────
    if model_type == "ollama":
        from langchain_ollama import ChatOllama

        if model_name is None:
            has_gpu = _detect_gpu()
            if has_gpu:
                model_name = OLLAMA_FAST_MODEL if tier == "fast" else OLLAMA_POWERFUL_MODEL
            else:
                model_name = OLLAMA_FALLBACK_FAST if tier == "fast" else OLLAMA_FALLBACK_POWER

        print(f"[LLM] Ollama/{model_name} (tier={tier}, temp={_temp})")
        return ChatOllama(model=model_name, temperature=_temp)

    # ── Groq (free cloud API — LPU, ultra-fast) ──────────────────────────────
    elif model_type == "groq":
        from langchain_groq import ChatGroq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com"
            )

        if model_name is None:
            model_name = GROQ_FAST_MODEL if tier == "fast" else GROQ_POWERFUL_MODEL

        print(f"[LLM] Groq/{model_name} (tier={tier}, temp={_temp})")
        return ChatGroq(
            model=model_name,
            api_key=api_key,
            temperature=_temp,
            max_retries=3
        )

    # ── Gemini 2.0 Flash (Google AI Studio free) ─────────────────────────────
    elif model_type == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Get a free key at https://aistudio.google.com"
            )

        if model_name is None:
            model_name = GEMINI_MODEL  # gemini-2.0-flash for both tiers

        print(f"[LLM] Gemini/{model_name} (tier={tier}, temp={_temp})")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=_temp,
            max_retries=3
        )

    else:
        raise ValueError(
            f"Unknown model_type: '{model_type}'. "
            "Choose from: 'ollama', 'groq', 'gemini'"
        )
