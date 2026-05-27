"""
tools/topic_suggestions.py
--------------------------
Smart topic suggestion engine for the Research Intelligence System.
Provides:
  - Curated trending research topics organized by domain
  - Prefix-based autocomplete for the search bar
  - Random topic picker
"""

import random

# ── Curated trending topics by domain ─────────────────────────────────────────
TRENDING_TOPICS = {
    "Artificial Intelligence": [
        "Large Language Models and Hallucination Reduction Techniques",
        "Multimodal AI: Combining Vision, Audio, and Language",
        "AI Agents and Autonomous Decision Making",
        "Retrieval-Augmented Generation (RAG) in Production",
        "Constitutional AI and AI Alignment Research",
        "Open-Source LLMs vs Proprietary Models: A 2026 Comparison",
        "AI in Drug Discovery and Pharmaceutical Research",
        "Mixture of Experts (MoE) Architecture in Modern LLMs",
        "Chain-of-Thought Prompting and Reasoning in AI",
        "AI Governance and Regulatory Frameworks Worldwide",
    ],
    "Machine Learning": [
        "Federated Learning for Privacy-Preserving AI",
        "Transformer Architecture Innovations Beyond Attention",
        "Transfer Learning and Foundation Models",
        "Reinforcement Learning from Human Feedback (RLHF)",
        "Neural Architecture Search and AutoML",
        "Explainable AI and Interpretability Methods",
        "Few-Shot and Zero-Shot Learning Techniques",
        "Quantization and Model Compression for Edge AI",
        "Graph Neural Networks for Molecular Design",
        "Continual Learning and Catastrophic Forgetting",
    ],
    "Cybersecurity": [
        "AI-Powered Cybersecurity Threat Detection",
        "Zero Trust Security Architecture in Cloud Environments",
        "Quantum Cryptography and Post-Quantum Security",
        "Ransomware Evolution and Defense Strategies",
        "Supply Chain Attacks: SolarWinds to 2026",
        "Adversarial Attacks on Machine Learning Models",
        "Deepfake Detection and Digital Media Authenticity",
        "Privacy-Preserving Machine Learning",
        "LLM Security: Prompt Injection and Jailbreaks",
        "Biometric Authentication Systems and Vulnerabilities",
    ],
    "Quantum Computing": [
        "Quantum Error Correction: Current State and Milestones",
        "Quantum Machine Learning Algorithms",
        "Superconducting Qubits vs Trapped Ion Quantum Computers",
        "Quantum Advantage and Real-World Quantum Supremacy",
        "Quantum Networking and the Quantum Internet",
        "IBM Quantum and Google Quantum AI Progress in 2026",
        "Quantum Chemistry Simulations",
        "Quantum Annealing for Optimization Problems",
    ],
    "Biotechnology": [
        "CRISPR-Cas9 Gene Editing: Clinical Applications",
        "mRNA Technology Beyond COVID-19 Vaccines",
        "Synthetic Biology and Engineered Microorganisms",
        "AI-Assisted Protein Structure Prediction (AlphaFold)",
        "Personalized Medicine and Genomic Sequencing",
        "Longevity Research and Anti-Aging Science",
        "Cell and Gene Therapy Clinical Trials",
        "Microbiome Research and Gut-Brain Connection",
    ],
    "Renewable Energy": [
        "Solid-State Battery Technology for Electric Vehicles",
        "Perovskite Solar Cells: Efficiency Records in 2026",
        "Green Hydrogen Production and Storage",
        "Nuclear Fusion: ITER and Private Fusion Companies",
        "Grid-Scale Energy Storage Technologies",
        "Carbon Capture and Direct Air Capture Technology",
        "Offshore Wind Energy Developments",
        "Smart Grid and AI-Optimized Energy Systems",
    ],
    "Space Technology": [
        "SpaceX Starship and the Future of Space Transport",
        "Artemis Program: Return to the Moon",
        "Mars Colonization: Engineering Challenges",
        "CubeSats and Commercial Space Revolution",
        "Space Debris and Orbital Cleanup Technologies",
        "Gravitational Wave Astronomy with LIGO",
        "James Webb Space Telescope Discoveries",
        "Asteroid Mining: Commercial Viability Analysis",
    ],
    "Healthcare & Medicine": [
        "AI Diagnostics in Radiology and Pathology",
        "Wearable Health Technology and Continuous Monitoring",
        "Digital Therapeutics and Mental Health Apps",
        "Telemedicine Adoption Post-Pandemic",
        "Robotic Surgery Advances: Da Vinci and Beyond",
        "Neuroscience of Memory and Alzheimer's Research",
        "Microplastics in Human Blood: Health Implications",
        "AI-Powered Drug Repurposing",
    ],
}

# All topics flat list for searching
ALL_TOPICS = [topic for topics in TRENDING_TOPICS.values() for topic in topics]


def get_suggestions(query: str, max_results: int = 5) -> list[str]:
    """
    Return topic suggestions matching the user's query (prefix/substring match).
    Case-insensitive. Returns up to max_results suggestions.
    """
    if not query or len(query) < 2:
        return []
    query_lower = query.lower()
    matches = [t for t in ALL_TOPICS if query_lower in t.lower()]
    return matches[:max_results]


def get_random_topic() -> str:
    """Return a random trending topic."""
    return random.choice(ALL_TOPICS)


def get_topics_by_domain(domain: str) -> list[str]:
    """Return all topics for a given domain."""
    return TRENDING_TOPICS.get(domain, [])


def get_all_domains() -> list[str]:
    """Return all domain names."""
    return list(TRENDING_TOPICS.keys())


def get_random_topic_by_domain(domain: str) -> str:
    """Return a random topic from a specific domain."""
    topics = TRENDING_TOPICS.get(domain, ALL_TOPICS)
    return random.choice(topics)
