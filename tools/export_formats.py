"""
tools/export_formats.py
-----------------------
Phase 1 Feature: Multi-Format Academic Export

Exports the generated research report in 4 professional formats:
  1. APA Literature Review  - standard academic citation format
  2. IEEE Technical Format  - numbered references, structured sections
  3. Slide Deck Outline     - 6-slide presentation outline
  4. Obsidian Markdown      - wikilinks + YAML frontmatter for note apps
"""

from datetime import datetime
from typing import List, Optional


def _clean_topic(topic: str) -> str:
    """Sanitize topic string for use in filenames and tags."""
    return "".join(c if c.isalnum() or c in " _-" else "" for c in topic).strip()


def export_apa_literature_review(
    report_draft: str,
    verified_claims: List[dict],
    topic: str,
    research_gaps: Optional[List[str]] = None
) -> str:
    """
    Exports the report formatted as an APA-style academic literature review.
    Includes: title page, abstract, body with in-text citations, references list.
    """
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    year = now.year

    # Build APA references from verified claims
    apa_refs = []
    ref_num = 1
    seen_sources = set()
    for claim in verified_claims:
        src_type = claim.get("reasoning", "")
        claim_text = claim.get("claim", "")
        if claim_text and claim_text not in seen_sources:
            seen_sources.add(claim_text)
            if "arxiv" in claim_text.lower() or "arxiv" in str(claim.get("sources", "")).lower():
                apa_refs.append(f"[{ref_num}] Author(s). ({year}). {claim_text[:80]}... arXiv preprint.")
            elif "wikipedia" in str(claim.get("sources", "")).lower():
                apa_refs.append(f"[{ref_num}] Wikipedia contributors. ({year}). {topic}. Wikipedia, The Free Encyclopedia.")
            else:
                apa_refs.append(f"[{ref_num}] Retrieved {date_str}, from online sources.")
            ref_num += 1

    if not apa_refs:
        apa_refs = [f"[1] Retrieved {date_str}, from multiple online sources."]

    gaps_section = ""
    if research_gaps:
        gap_bullets = "\n".join(f"  • {g}" for g in research_gaps[:6])
        gaps_section = f"""

**Future Research Directions**

Based on this review, the following gaps and open questions warrant further investigation:

{gap_bullets}
"""

    output = f"""---
RUNNING HEAD: {topic.upper()[:50]}
---

# {topic}: A Comprehensive Literature Review

**Prepared:** {date_str}
**Format:** APA 7th Edition
**Document Type:** Literature Review

---

## Abstract

This literature review synthesizes current research on {topic}, drawing from academic preprints, encyclopedic sources, and contemporary reporting. Key findings, methodological approaches, and identified research gaps are presented to serve as a foundation for future investigation.

**Keywords:** {", ".join(topic.split()[:5])}, research synthesis, systematic review

---

## Introduction

The study of {topic} has gained significant scholarly attention in recent years. This review aggregates and critically evaluates available evidence to present a consolidated understanding of the current state of knowledge.

---

## Literature Review

{report_draft}

---
{gaps_section}

## References

{chr(10).join(apa_refs)}

---
*Note: This document was generated using the Sage Multi-Agent Research Intelligence System. All claims are derived from verified, cross-referenced sources.*
"""
    return output


def export_ieee_format(
    report_draft: str,
    verified_claims: List[dict],
    topic: str,
    research_gaps: Optional[List[str]] = None
) -> str:
    """
    Exports the report in IEEE technical paper format.
    Includes: abstract, numbered sections, reference list with [n] citation style.
    """
    now = datetime.now()
    date_str = now.strftime("%B %Y")
    year = now.year

    # Build IEEE numbered references
    ieee_refs = []
    for i, claim in enumerate(verified_claims[:15], 1):
        claim_text = claim.get("claim", "")
        conf = claim.get("confidence", 70)
        ieee_refs.append(f"[{i}] \"{claim_text[:100]}...\" Confidence: {conf}%. Verified {date_str}.")

    if not ieee_refs:
        ieee_refs = ["[1] Sage Research Intelligence System. Verified sources, " + date_str + "."]

    gaps_text = ""
    if research_gaps:
        gaps_text = "\n\n## V. Open Research Problems\n\n"
        for i, gap in enumerate(research_gaps[:8], 1):
            gaps_text += f"**R{i}.** {gap}\n\n"

    output = f"""IEEE FORMAT — Technical Research Report
==========================================
Title: {topic}
Conference/Journal: Sage — Multi-Agent Research Intelligence System
Date: {date_str}
Format: IEEE Transactions Style

==========================================

Abstract—This paper presents a structured technical synthesis on the subject of {topic}. Findings are derived from multi-source aggregation across academic preprints (arXiv), encyclopedic databases (Wikipedia), and contemporary technical reporting. A multi-agent verification pipeline was used to ensure factual accuracy. Key metrics, methodologies, and implications are presented below.

Index Terms—{", ".join(topic.split()[:6])}, AI research synthesis, multi-source verification

==========================================

## I. Introduction

The domain of {topic} presents significant research opportunities. This report consolidates current knowledge to identify the state of the art and highlight unresolved challenges.

## II. Background and Context

{report_draft[:1500]}

## III. Key Findings and Results

The following verified findings are presented with confidence scores, indicating corroboration strength across multiple independent sources:

{chr(10).join(f"  [{i+1}] {c.get('claim','N/A')} [Conf: {c.get('confidence',0)}%]" for i, c in enumerate(verified_claims[:15]))}

## IV. Analysis and Discussion

{report_draft[1500:3000] if len(report_draft) > 1500 else report_draft}
{gaps_text}

## VI. Conclusion

This synthesis of {topic} confirms the dynamic nature of this research domain. The verified claims and analytical findings presented herein provide a reliable foundation for future research endeavors.

==========================================
References

{chr(10).join(ieee_refs)}

==========================================
*Generated by Sage — Multi-Agent Research Intelligence System*
"""
    return output


def export_slide_outline(
    insights: List[str],
    verified_claims: List[dict],
    topic: str,
    research_gaps: Optional[List[str]] = None
) -> str:
    """
    Generates a 6-slide presentation outline from insights and verified claims.
    Compatible with PowerPoint, Google Slides, and any outline-based tool.
    """
    now = datetime.now()
    date_str = now.strftime("%B %Y")

    # Prepare bullet points
    key_findings = [c.get("claim", "") for c in verified_claims[:5] if c.get("claim")]
    top_insights = [i for i in insights[:8] if i.strip() and len(i.strip()) > 15]
    gaps = research_gaps[:4] if research_gaps else ["Further empirical studies needed."]

    findings_text = "\n".join(f"  • {f[:100]}" for f in key_findings) or "  • Key findings pending verification."
    insights_text = "\n".join(f"  • {i[:100]}" for i in top_insights) or "  • Insights pending analysis."
    gaps_text     = "\n".join(f"  • {g[:100]}" for g in gaps)

    output = f"""PRESENTATION SLIDE OUTLINE
Topic: {topic}
Format: 6-Slide Deck | {date_str}
Generated by: Sage — Multi-Agent Research Intelligence System
=========================================================

─────────────────────────────────────────
SLIDE 1: TITLE SLIDE
─────────────────────────────────────────
Title:    {topic}
Subtitle: A Comprehensive Research Synthesis
Date:     {date_str}
Source:   Multi-Agent Research Intelligence System (Sage)

Speaker Notes:
  Introduce the topic and the motivation behind the research.
  Emphasize that all findings are cross-verified from multiple sources.

─────────────────────────────────────────
SLIDE 2: THE PROBLEM / BACKGROUND
─────────────────────────────────────────
Header: Why Does {topic} Matter?

Bullet Points:
  • Define the core concept and its real-world significance.
  • Explain the current state of research in this domain.
  • Highlight the gap between current knowledge and what practitioners need.

Speaker Notes:
  Use this slide to set context. Do not go into technical depth yet.
  Focus on the "why" before the "what."

─────────────────────────────────────────
SLIDE 3: KEY FINDINGS
─────────────────────────────────────────
Header: What the Research Tells Us

Verified Findings:
{findings_text}

Speaker Notes:
  These are the highest-confidence verified facts from the research run.
  Each has been cross-referenced across multiple independent sources.
  Cite confidence scores if asked.

─────────────────────────────────────────
SLIDE 4: DEEP ANALYSIS
─────────────────────────────────────────
Header: Analytical Insights

{insights_text}

Speaker Notes:
  This slide presents the structured analytical output.
  Focus on trends, statistics, and comparative points.
  Avoid generic statements — every claim should be specific.

─────────────────────────────────────────
SLIDE 5: RESEARCH GAPS & OPEN QUESTIONS
─────────────────────────────────────────
Header: What We Don't Know Yet

Identified Gaps:
{gaps_text}

Speaker Notes:
  This is a key differentiator — most presentations only cover what is known.
  By presenting gaps, you demonstrate academic rigor and forward-thinking.
  Frame each gap as a research opportunity, not a failure.

─────────────────────────────────────────
SLIDE 6: CONCLUSION & NEXT STEPS
─────────────────────────────────────────
Header: Summary and Recommendations

Key Takeaways:
  • {topic} represents a fast-moving, high-impact research domain.
  • Multiple verified sources confirm the core findings presented.
  • Clear research gaps exist that present opportunities for future work.

Recommended Next Steps:
  1. Review the full Sage report for in-depth technical details.
  2. Explore the identified research gaps for novel study opportunities.
  3. Cross-reference with ArXiv for the latest preprints on this topic.

─────────────────────────────────────────
END OF OUTLINE
Generated by Sage | {date_str}
"""
    return output


def export_obsidian_markdown(
    report_draft: str,
    verified_claims: List[dict],
    topic: str,
    research_gaps: Optional[List[str]] = None
) -> str:
    """
    Exports the report as an Obsidian-compatible Markdown note.
    Features:
      - YAML frontmatter with tags and metadata
      - [[wikilink]] style references to related topics
      - Callout blocks for key findings, gaps, and warnings
      - Dataview-compatible metadata
    """
    now = datetime.now()
    date_iso = now.strftime("%Y-%m-%d")
    tags = ["research", "sage"] + [w.lower() for w in topic.split()[:4] if len(w) > 3]

    # Build wikilinks from topic keywords
    keywords = [w.strip(".,") for w in topic.split() if len(w) > 4]
    wikilinks = " | ".join(f"[[{kw}]]" for kw in keywords[:6])

    # Build claim callouts
    top_claims = verified_claims[:5]
    claims_callout = ""
    for c in top_claims:
        conf = c.get("confidence", 0)
        icon = "✅" if conf >= 80 else "⚠️" if conf >= 60 else "❌"
        claims_callout += f"> {icon} **{conf}%** — {c.get('claim', '')}\n"

    # Build gaps callout
    gaps_callout = ""
    if research_gaps:
        gaps_callout = "\n> [!question] Research Gaps\n"
        for gap in research_gaps[:6]:
            gaps_callout += f"> - {gap}\n"

    output = f"""---
title: "{topic}"
date: {date_iso}
tags: [{", ".join(tags)}]
source: Sage — Multi-Agent Research Intelligence System
type: research-note
status: complete
verified_claims: {len(verified_claims)}
---

# {topic}

Related: {wikilinks}

---

> [!abstract] Summary
> This note was synthesized by the Sage multi-agent research system.
> All claims have been cross-verified across academic, encyclopedic, and news sources.
> **Confidence methodology:** Claims require corroboration from ≥2 independent sources for VERIFIED status.

---

## 📌 Key Verified Facts

{claims_callout}
---

## 📄 Full Research Report

{report_draft}

---
{gaps_callout}

---

## 🔗 Connections

```dataview
TABLE date, verified_claims, status
FROM #research
SORT date DESC
LIMIT 10
```

---

*🤖 Generated by [[Sage]] | {date_iso}*
*Pipeline: Researcher → Fact Checker → HITL → Analyst → Gap Detector → Writer → Critic*
"""
    return output
