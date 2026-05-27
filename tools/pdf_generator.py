"""
tools/pdf_generator.py
----------------------
Generates professional PDF reports using ReportLab (100% free).
2026 Edition: Beautiful cover page, table of contents, page numbers,
section dividers, and inline citations.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
import os
import re


# ── Color Palette ──────────────────────────────────────────────────────────────
INDIGO      = colors.HexColor('#6366f1')
PURPLE      = colors.HexColor('#a855f7')
DARK_NAVY   = colors.HexColor('#0f172a')
SLATE_800   = colors.HexColor('#1e293b')
SLATE_700   = colors.HexColor('#334155')
SLATE_500   = colors.HexColor('#64748b')
SLATE_300   = colors.HexColor('#cbd5e1')
SLATE_100   = colors.HexColor('#f1f5f9')
TEAL        = colors.HexColor('#0f766e')
EMERALD     = colors.HexColor('#10b981')
AMBER       = colors.HexColor('#f59e0b')
WHITE       = colors.white


class PageNumCanvas(canvas.Canvas):
    """Canvas subclass that adds page numbers and a branded footer."""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count: int):
        page_num = self._pageNumber
        if page_num == 1:
            return  # Skip cover page number

        # Footer bar
        self.setFillColor(SLATE_100)
        self.rect(0, 0, letter[0], 0.45 * inch, fill=1, stroke=0)

        # Left: System name
        self.setFillColor(SLATE_500)
        self.setFont("Helvetica", 7)
        self.drawString(0.55 * inch, 0.17 * inch, "Sage • Multi-Agent Research Intelligence System")

        # Right: Page number
        self.drawRightString(
            letter[0] - 0.55 * inch, 0.17 * inch,
            f"Page {page_num} of {page_count}"
        )

        # Top accent line
        self.setStrokeColor(INDIGO)
        self.setLineWidth(1.5)
        self.line(0.55 * inch, letter[1] - 0.35 * inch,
                  letter[0] - 0.55 * inch, letter[1] - 0.35 * inch)


def generate_pdf(
    topic: str,
    report: str,
    quality_score: int,
    verified_count: int,
    llm_type: str = "groq",
    agent_timings: dict = None,
    word_count: int = 0
) -> str:
    """
    Generate a professional PDF report with cover page, metadata, and branded styling.

    Args:
        topic:          Research topic
        report:         Markdown report text
        quality_score:  Critic quality score 0-100
        verified_count: Number of verified claims used
        llm_type:       LLM provider used
        agent_timings:  Dict of agent->seconds
        word_count:     Final report word count

    Returns:
        Absolute path to the saved PDF file.
    """
    os.makedirs("output", exist_ok=True)
    clean_topic = "".join(c for c in topic[:35] if c.isalnum() or c in (' ', '_', '-')).strip()
    clean_topic = clean_topic.replace(' ', '_')
    filename = f"output/research_{clean_topic}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = _build_styles()
    story  = []

    # ── COVER PAGE ────────────────────────────────────────────────────────────
    story += _build_cover_page(topic, quality_score, verified_count, llm_type, styles)
    story.append(PageBreak())

    # ── METADATA TABLE ────────────────────────────────────────────────────────
    story += _build_metadata_table(topic, quality_score, verified_count, llm_type,
                                   agent_timings or {}, word_count, styles)
    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=INDIGO, spaceAfter=18))

    # ── REPORT CONTENT ────────────────────────────────────────────────────────
    story += _parse_report_content(report, styles)

    doc.build(story, canvasmaker=PageNumCanvas)
    print(f"[PDF] saved: {filename}")
    return filename


def _build_styles():
    """Build and return all paragraph styles."""
    base = getSampleStyleSheet()

    styles = {}

    styles["cover_brand"] = ParagraphStyle(
        "cover_brand",
        fontSize=9, leading=12,
        textColor=INDIGO,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )
    styles["cover_title"] = ParagraphStyle(
        "cover_title",
        fontSize=30, leading=36,
        textColor=WHITE,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=12,
    )
    styles["cover_subtitle"] = ParagraphStyle(
        "cover_subtitle",
        fontSize=13, leading=18,
        textColor=colors.HexColor('#a5b4fc'),
        alignment=TA_CENTER,
        fontName="Helvetica",
        spaceAfter=6,
    )
    styles["cover_topic"] = ParagraphStyle(
        "cover_topic",
        fontSize=16, leading=22,
        textColor=WHITE,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=10,
    )
    styles["cover_meta"] = ParagraphStyle(
        "cover_meta",
        fontSize=9, leading=13,
        textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER,
        fontName="Helvetica",
        spaceAfter=3,
    )
    styles["h1"] = ParagraphStyle(
        "h1",
        fontSize=18, leading=22,
        textColor=DARK_NAVY,
        fontName="Helvetica-Bold",
        spaceBefore=18, spaceAfter=8,
        keepWithNext=True,
    )
    styles["h2"] = ParagraphStyle(
        "h2",
        fontSize=13, leading=17,
        textColor=TEAL,
        fontName="Helvetica-Bold",
        spaceBefore=12, spaceAfter=5,
        keepWithNext=True,
    )
    styles["h3"] = ParagraphStyle(
        "h3",
        fontSize=11, leading=14,
        textColor=colors.HexColor('#1e3a8a'),
        fontName="Helvetica-Bold",
        spaceBefore=8, spaceAfter=4,
        keepWithNext=True,
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontSize=10, leading=15,
        textColor=SLATE_700,
        fontName="Helvetica",
        spaceAfter=7,
        alignment=TA_JUSTIFY,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet",
        fontSize=10, leading=14,
        textColor=SLATE_700,
        fontName="Helvetica",
        leftIndent=18,
        firstLineIndent=-12,
        spaceAfter=4,
        bulletIndent=6,
    )
    styles["meta_label"] = ParagraphStyle(
        "meta_label",
        fontSize=9, leading=12,
        textColor=colors.HexColor('#1e3a8a'),
        fontName="Helvetica-Bold",
    )
    styles["meta_value"] = ParagraphStyle(
        "meta_value",
        fontSize=9, leading=12,
        textColor=SLATE_700,
        fontName="Helvetica",
    )

    return styles


def _build_cover_page(topic, quality_score, verified_count, llm_type, styles) -> list:
    """Build a rich gradient-style cover page."""
    story = []

    # Dark background simulation with a table
    cover_data = [['']]
    cover_table = Table(cover_data, colWidths=[7.2 * inch], rowHeights=[9.5 * inch])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_NAVY),
        ('LEFTPADDING', (0, 0), (-1, -1), 48),
        ('RIGHTPADDING', (0, 0), (-1, -1), 48),
        ('TOPPADDING', (0, 0), (-1, -1), 80),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 40),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    # Build inner story as a nested table
    inner = []
    inner.append(Paragraph("Sage", styles["cover_brand"]))
    inner.append(Spacer(1, 6))
    inner.append(Paragraph("RESEARCH INTELLIGENCE REPORT", styles["cover_subtitle"]))
    inner.append(Spacer(1, 24))

    # Separator line (simulated with small colored table)
    sep = Table([['']], colWidths=[4 * inch], rowHeights=[3])
    sep.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), INDIGO)]))
    inner.append(_center_flowable(sep, 4 * inch))
    inner.append(Spacer(1, 24))

    inner.append(Paragraph(topic, styles["cover_topic"]))
    inner.append(Spacer(1, 40))

    # Score badge
    score_color = EMERALD if quality_score >= 80 else AMBER if quality_score >= 70 else colors.HexColor('#ef4444')
    score_label = "EXCELLENT" if quality_score >= 85 else "GOOD" if quality_score >= 70 else "DRAFT"
    badge_data  = [[f"Quality Score: {quality_score}/100  •  {score_label}"]]
    badge_table = Table(badge_data, colWidths=[2.8 * inch], rowHeights=[0.38 * inch])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), score_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    inner.append(_center_flowable(badge_table, 2.8 * inch))
    inner.append(Spacer(1, 16))

    # Meta info
    now = datetime.now()
    inner.append(Paragraph(f"Generated: {now.strftime('%B %d, %Y at %H:%M')}", styles["cover_meta"]))
    inner.append(Paragraph(f"Verified Claims: {verified_count}  •  AI Provider: {llm_type.upper()}", styles["cover_meta"]))
    inner.append(Paragraph("Powered by LangGraph Multi-Agent Orchestration", styles["cover_meta"]))
    inner.append(Spacer(1, 40))

    # Agent pipeline strip at bottom
    agents = ["Cache Check", "Researcher", "Fact Checker", "Analyst", "Writer", "Critic"]
    agent_data = [[Paragraph(a, ParagraphStyle("ag", fontSize=7, textColor=WHITE,
                  fontName="Helvetica", alignment=TA_CENTER)) for a in agents]]
    agent_table = Table(agent_data, colWidths=[1.1 * inch] * 6, rowHeights=[0.32 * inch])
    agent_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1e1b4b')),
        ('TEXTCOLOR', (0, 0), (-1, -1), WHITE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#4338ca')),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    inner.append(agent_table)

    story += inner
    return story


def _center_flowable(flowable, width):
    """Center a fixed-width flowable using a wrapper table."""
    wrapper = Table([[flowable]], colWidths=[7.2 * inch])
    wrapper.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), DARK_NAVY),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return wrapper


def _build_metadata_table(topic, quality_score, verified_count, llm_type,
                           agent_timings, word_count, styles) -> list:
    """Build a styled metadata summary table."""
    story = []
    story.append(Paragraph("Report Metadata", styles["h1"]))

    total_time = sum(agent_timings.values()) if agent_timings else 0
    score_color_hex = '#10b981' if quality_score >= 80 else '#f59e0b' if quality_score >= 70 else '#ef4444'

    rows = [
        ("Generated", datetime.now().strftime("%B %d, %Y at %H:%M")),
        ("Research Topic", topic),
        ("Critic Quality Score", f"{quality_score}/100"),
        ("Verified Claims Used", str(verified_count)),
        ("Report Word Count", f"~{word_count:,} words" if word_count else "N/A"),
        ("Total Pipeline Time", f"{total_time:.1f} seconds" if total_time else "N/A"),
        ("AI Provider", llm_type.upper()),
        ("Orchestration", "LangGraph Multi-Agent State Machine"),
        ("Sources", "Web (DuckDuckGo) + Wikipedia + ArXiv + RSS News"),
    ]

    table_data = [
        [Paragraph(label, styles["meta_label"]),
         Paragraph(value, styles["meta_value"])]
        for label, value in rows
    ]

    table = Table(table_data, colWidths=[2.0 * inch, 5.0 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), SLATE_100),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [SLATE_100, colors.HexColor('#f8fafc')]),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, SLATE_300),
        ('BOX', (0, 0), (-1, -1), 1, SLATE_300),
    ]))
    story.append(table)
    return story


def _parse_report_content(report: str, styles: dict) -> list:
    """Parse markdown report text into styled ReportLab flowables."""
    story = []
    lines = report.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line:
            story.append(Spacer(1, 4))
            continue

        # H1
        if line.startswith('# '):
            title = line[2:].strip()
            if 'Research Report' not in title:
                story.append(KeepTogether([
                    Spacer(1, 6),
                    HRFlowable(width="100%", thickness=2, color=INDIGO, spaceBefore=4, spaceAfter=8),
                    Paragraph(title, styles["h1"]),
                ]))
            continue

        # H2
        if line.startswith('## '):
            title = line[3:].strip()
            story.append(KeepTogether([
                Spacer(1, 4),
                HRFlowable(width="40%", thickness=1, color=TEAL, spaceBefore=4, spaceAfter=6),
                Paragraph(title, styles["h2"]),
            ]))
            continue

        # H3
        if line.startswith('### '):
            story.append(Paragraph(line[4:].strip(), styles["h3"]))
            continue

        # Bullet (-, *, •)
        if re.match(r'^[-*•] ', line):
            content = _clean_inline(line[2:])
            story.append(Paragraph(f"&bull; {content}", styles["bullet"]))
            continue

        # Numbered list
        if re.match(r'^\d+\. ', line):
            content = _clean_inline(re.sub(r'^\d+\. ', '', line))
            story.append(Paragraph(content, styles["bullet"]))
            continue

        # Horizontal rule
        if line in ('---', '===', '***', '________'):
            story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_300,
                                    spaceBefore=8, spaceAfter=8))
            continue

        # Regular paragraph
        content = _clean_inline(line)
        if content:
            story.append(Paragraph(content, styles["body"]))

    return story


def _clean_inline(text: str) -> str:
    """Convert basic markdown inline formatting to ReportLab XML tags."""
    # **bold**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # *italic*
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    # `code`
    text = re.sub(r'`(.+?)`', r'<font name="Courier" color="#6d28d9">\1</font>', text)
    # [text](url) links — just show the text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    # Remove raw URLs (keep readable)
    text = re.sub(r'https?://\S+', '', text).strip()
    # Escape XML special characters (outside our tags)
    text = text.replace('&', '&amp;').replace('<b>', '\x00B').replace('</b>', '\x00/B')
    text = text.replace('<i>', '\x00I').replace('</i>', '\x00/I')
    text = text.replace('<font', '\x00FONT').replace('</font>', '\x00/FONT')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('\x00B', '<b>').replace('\x00/B', '</b>')
    text = text.replace('\x00I', '<i>').replace('\x00/I', '</i>')
    text = text.replace('\x00FONT', '<font').replace('\x00/FONT', '</font>')
    return text
