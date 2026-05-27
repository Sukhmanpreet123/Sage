# Sage 🧠 • Multi-Agent Research Intelligence System

Sage is an advanced, production-grade **multi-agent AI system** built using **LangGraph** where 5 specialized agents cooperate autonomously to produce peer-reviewed, fact-checked research papers.

This application is built for 2026 enterprise requirements and is **100% free**—running entirely on your laptop or using free-tier cloud models with zero cost.

---

## 🏗️ System Architecture

The project models the core cognitive workflow of human research departments through stateful graph orchestrations:

```
                  ╔══════════════════════════════════════╗
                  ║         USER INTERFACE LAYER         ║
                  ║       Streamlit Interactive App      ║
                  ╚══════════════════════════════════════╝
                                     │
                                     ▼
                  ╔══════════════════════════════════════╗
                  ║        LANGGRAPH WORKFLOW STATE      ║
                  ║                                      ║
                  ║  ┌─────────┐      ┌───────────────┐  ║
                  ║  │  START  │ ───▶ │  RESEARCHER   │  ║
                  ║  └─────────┘      │ DuckDuckGo/   │  ║
                  ║                   │ Wiki / ArXiv  │  ║
                  ║                   └───────┬───────┘  ║
                  ║                           │          ║
                  ║                   ┌───────▼───────┐  ║
                  ║                   │ FACT CHECKER  │  ║
                  ║                   │ Deduplication │  ║
                  ║                   └───────┬───────┘  ║
                  ║                           │          ║
                  ║                   ┌───────▼───────┐  ║
                  ║                   │    ANALYST    │  ║
                  ║                   │  Quantitative │  ║
                  ║                   └───────┬───────┘  ║
                  ║                           │          ║
                  ║                   ┌───────▼───────┐  ║
                  ║    ┌────────────▶ │    WRITER     │  ║
                  ║    │              │ Draft Report  │  ║
                  ║    │              └───────┬───────┘  ║
                  ║    │                      │          ║
                  ║    │              ┌───────▼───────┐  ║
                  ║  [Score < 70]     │    CRITIC     │  ║
                  ║    │              │  Rubric Gate  │  ║
                  ║    └──────────────│  Score: 0-100 │  ║
                  ║                   └───────┬───────┘  ║
                  ║                           │          ║
                  ║                     [Score >= 70]    ║
                  ║                           │          ║
                  ║                           ▼          ║
                  ║                   ┌───────────────┐  ║
                  ║                   │ PDF GENERATOR │ ──▶ END
                  ║                   └───────────────┘  ║
                  ╚══════════════════════════════════════╝
```

---

## 🤖 The 5-Agent Hierarchy

| Agent | Core Objective | LLM Engine | Source Databases / Tools |
| :--- | :--- | :--- | :--- |
| **🔍 Researcher** | Aggregate data points from multiple public databases | Llama 3.2 | DuckDuckGo Web, Wikipedia API, arXiv Papers, RSS Feeds |
| **🛡️ Fact Checker** | Identify and weed out hallucinated figures, verifying facts | Mistral | Strict 2-source confirmation & authority logic |
| **📊 Analyst** | Extract key statistics, quantitative changes, and strategic trends | Llama 3.2 | Claims semantic analysis |
| **✍️ Writer** | Build a cohesive, detailed academic markdown publication | Llama 3.2 | Grounded structure compiler |
| **🧐 Critic** | Perform grading and issue feedback loops for iterative edits | Mistral | Weighted rubric scoring (Accuracy/Clarity/Completeness) |

---

## 💡 Key Features

- **Zero Hallucination Pipeline:** Fact Checker cross-verifies all web results; unverified single-source claims are marked uncertain or removed.
- **Dynamic Quality Control:** The Critic agent grades reports out of 100. If quality is below 70, it automatically loops back to the Writer with specific change feedback (capped at 3 iterations).
- **High-Resolution PDF Generation:** Generates clean, ready-to-publish PDFs complete with stylized headings, structural tables, and source indices using ReportLab.
- **Dynamic Model Selection:** Switch on the fly in the Streamlit Sidebar between **Ollama** (completely local), **Groq** (free fast cloud API), and **Gemini** (free Google AI Studio API).
- **Observability Integrated:** Compatible with LangSmith out of the box for real-time telemetry tracing.

---

## ⚡ Quick Start

### 1. Prerequisite: Local LLMs
Install [Ollama](https://ollama.com) and serve Llama 3.2 and Mistral models:
```bash
ollama pull llama3.2
ollama pull mistral
```

### 2. Setup the Repository
```bash
git clone https://github.com/yourusername/intel-agent-research-system.git
cd intel-agent-research-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in cloud keys if you plan to use Groq/Gemini tiers instead of local Ollama:
```bash
cp .env.example .env
```

### 4. Fire It Up
Start the premium Streamlit interactive dashboard:
```bash
streamlit run app/streamlit_app.py
```
Open your browser at `http://localhost:8501`.

---

## 📊 Evaluation Rubric (Critic Agent)

The Critic agent scores drafts on three core metrics:
- **Accuracy (40%):** Ensures no qualitative assumptions or fake statistics are present.
- **Completeness (30%):** Guarantees all key data points from the verification stage are featured.
- **Clarity (30%):** Measures readability, academic style formatting, and logical flow.

---

## 📁 Repository Structure
```
research-intelligence-system/
│
├── 📁 agents/                     # Specialized Agent Logic
│   ├── researcher.py              # Agent 1: Search aggregator
│   ├── fact_checker.py            # Agent 2: Claim verification
│   ├── analyst.py                 # Agent 3: Metric extraction
│   ├── writer.py                  # Agent 4: Markdown draft writer
│   └── critic.py                  # Agent 5: Editorial rubric gate
│
├── 📁 graph/                      # LangGraph Control Flows
│   ├── state.py                   # TypedDict shared schema
│   └── workflow.py                # State graph and conditional routes
│
├── 📁 tools/                      # External Utilities
│   ├── search_tools.py            # Free DDG, Wiki, arXiv adapters
│   └── pdf_generator.py           # ReportLab PDF layout generator
│
├── 📁 llm/                        # Unified Model Loader
│   └── model_factory.py           # Dynamically loads Ollama/Groq/Gemini
│
├── 📁 app/                        # User Interface Dashboard
│   └── streamlit_app.py           # Streamlit app script
│
├── 📁 output/                     # Saved PDF report outputs
├── .env.example                   # Environment configuration template
├── requirements.txt               # Main dependencies
└── README.md                      # Documentation
```
