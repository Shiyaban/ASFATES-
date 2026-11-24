import io
from datetime import datetime
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle


def _cleanForHelvetica(text: str) -> str:
    replacements = {
        "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
        "\u2014": " - ", "\u2015": " - ",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u00a0": " ", "\u202f": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    text = text.encode("cp1252", errors="ignore").decode("cp1252")
    return escape(text)


def _buildChartsImage(df) -> io.BytesIO:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.6))

    colorMap = {
        "Positive": "#00d48a",
        "Neutral": "#636efa",
        "Negative": "#ef553b",
        "[LOW_CONFIDENCE]": "#ffa15a",
    }
    sCounts = df["sentiment"].value_counts()
    total = sCounts.sum()
    pieColors = [colorMap.get(label, "#95a5a6") for label in sCounts.index]

    wedges, _, autotexts = ax1.pie(
        sCounts.values,
        autopct=lambda p: f"{p:.0f}%" if p >= 5 else "",
        startangle=90,
        colors=pieColors,
        pctdistance=0.74,
        wedgeprops={"width": 0.48, "edgecolor": "white", "linewidth": 1.5},
    )
    for text in autotexts:
        text.set_color("white")
        text.set_fontweight("bold")
        text.set_fontsize(9)

    legendLabels = [f"{lbl} ({cnt / total * 100:.0f}%)" for lbl, cnt in zip(sCounts.index, sCounts.values)]
    ax1.legend(wedges, legendLabels, loc="center left", bbox_to_anchor=(0.95, 0.5), frameon=False)
    ax1.set_title("Sentiments Result", fontweight="bold")

    tCounts = df["theme"].value_counts()
    ax2.barh(tCounts.index[::-1], tCounts.values[::-1], color="#3498db")
    ax2.set_title("Themes Result", fontweight="bold")
    ax2.set_xlabel("Responses")
    ax2.xaxis.get_major_locator().set_params(integer=True)

    plt.tight_layout()
    imgBuf = io.BytesIO()
    fig.savefig(imgBuf, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    imgBuf.seek(0)
    return imgBuf


def exportPDF(
    df,
    summaryText: str,
    eventContext: str = "",
    questionContext: str = "",
    excludedCount: int = 0,
) -> bytes:
    pdfBuf = io.BytesIO()
    doc = SimpleDocTemplate(
        pdfBuf,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )

    styles = getSampleStyleSheet()
    titleStyle = ParagraphStyle("ReportTitle", parent=styles["Heading1"], fontSize=17, spaceAfter=4)
    subStyle = ParagraphStyle("SubTitle", parent=styles["Normal"], fontSize=9.5, textColor=colors.HexColor("#555555"), spaceAfter=10)
    h2Style = ParagraphStyle("SectionHeader", parent=styles["Heading2"], fontSize=12.5, spaceBefore=8, spaceAfter=4)
    bodyStyle = ParagraphStyle("BodyTextCustom", parent=styles["Normal"], fontSize=10, leading=13.5, spaceAfter=6)

    story = []

    eventTitle = _cleanForHelvetica(eventContext.strip()) if eventContext.strip() else "Campus Event Feedback Report"
    story.append(Paragraph(f"ASFATES - {eventTitle}", titleStyle))

    metaLines = [f"Generated: {datetime.now().strftime('%B %d, %Y %I:%M %p')}"]
    if questionContext.strip():
        metaLines.append(f"Survey Question: {_cleanForHelvetica(questionContext.strip())}")
    story.append(Paragraph(" | ".join(metaLines), subStyle))

    reviewCount = int(df["sentiment"].isin(["[LOW_CONFIDENCE]", "ERROR", "RL_ERROR"]).sum())
    metricsData = [
        ["Substantive Responses", "Excluded (N/A & Duplicates)", "Flagged for Review"],
        [str(len(df)), str(excludedCount), str(reviewCount)],
    ]
    metricsTable = Table(metricsData, colWidths=[2.35 * inch, 2.5 * inch, 2.35 * inch])
    metricsTable.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("FONTSIZE", (0, 1), (-1, 1), 12),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(metricsTable)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Sentiment & Theme Overview", h2Style))
    chartImg = Image(_buildChartsImage(df), width=6.9 * inch, height=2.45 * inch)
    story.append(chartImg)
    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph("Executive Summary", h2Style))
    for para in summaryText.strip().split("\n"):
        if para.strip():
            story.append(Paragraph(_cleanForHelvetica(para.strip()), bodyStyle))

    doc.build(story)
    pdfBuf.seek(0)
    return pdfBuf.getvalue()