from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdfcanvas
import os
from datetime import datetime
from xml.sax.saxutils import escape
from app.state.blackboard import ExpenseReportState

# Brand palette — kept in sync with the live app's theme (frontend/src/index.css
# --accent-primary / --accent-hover / --accent-light) so the PDF and the UI
# read as the same product.
BRAND_GREEN = colors.HexColor("#255C45")
BRAND_GREEN_DARK = colors.HexColor("#194831")
BRAND_GREEN_LIGHT = colors.HexColor("#E8F1E9")
BRAND_GREEN_TINT = colors.HexColor("#CFE3D6")
TEXT_DARK = colors.HexColor("#192720")
TEXT_MUTED = colors.HexColor("#55645D")
BORDER = colors.HexColor("#DDE4DC")
ROW_ALT = colors.HexColor("#F9FAF7")
WARNING_LIGHT = colors.HexColor("#FEF3E7")
WARNING_INK = colors.HexColor("#85560F")
ERROR_LIGHT = colors.HexColor("#FEE6E8")
ERROR_INK = colors.HexColor("#A12F3C")
NEUTRAL_LIGHT = colors.HexColor("#F2F3F0")

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch
BAND_HEIGHT = 0.9 * inch

STATUS_COLORS = {
    "eligible": (BRAND_GREEN_LIGHT, BRAND_GREEN_DARK),
    "accepted": (BRAND_GREEN_LIGHT, BRAND_GREEN_DARK),
    "held": (WARNING_LIGHT, WARNING_INK),
    "rejected": (ERROR_LIGHT, ERROR_INK),
}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="DocTitle", fontName="Helvetica-Bold", fontSize=20,
                           textColor=TEXT_DARK, spaceAfter=2))
    ss.add(ParagraphStyle(name="SectionHeading", fontName="Helvetica-Bold", fontSize=12,
                           textColor=BRAND_GREEN_DARK, spaceBefore=2, spaceAfter=2))
    ss.add(ParagraphStyle(name="Body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5,
                           textColor=TEXT_DARK, spaceAfter=3, leading=13))
    ss.add(ParagraphStyle(name="MetaLabel", fontName="Helvetica-Bold", fontSize=8.5,
                           textColor=TEXT_MUTED))
    ss.add(ParagraphStyle(name="MetaValue", fontName="Helvetica", fontSize=9.5,
                           textColor=TEXT_DARK))
    ss.add(ParagraphStyle(name="ClaimTitle", fontName="Helvetica-Bold", fontSize=10,
                           textColor=TEXT_DARK))
    ss.add(ParagraphStyle(name="ClaimBadge", fontName="Helvetica-Bold", fontSize=8.5))
    return ss


def _section_heading(text, styles):
    heading = Paragraph(text.upper(), styles["SectionHeading"])
    rule = HRFlowable(width="100%", thickness=1.2, color=BRAND_GREEN, spaceBefore=2, spaceAfter=8)
    return KeepTogether([heading, rule])


def _draw_letterhead(canvas_obj, doc):
    """Letterhead band drawn on every page — a text wordmark, not an image,
    so the report needs no external logo asset to render identically
    anywhere this project is checked out."""
    canvas_obj.saveState()
    canvas_obj.setFillColor(BRAND_GREEN)
    canvas_obj.rect(0, PAGE_H - BAND_HEIGHT, PAGE_W, BAND_HEIGHT, stroke=0, fill=1)
    canvas_obj.setFillColor(BRAND_GREEN_DARK)
    canvas_obj.rect(0, PAGE_H - BAND_HEIGHT - 3, PAGE_W, 3, stroke=0, fill=1)

    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 19)
    canvas_obj.drawString(MARGIN, PAGE_H - 0.48 * inch, "ExpenseFlow AI")
    canvas_obj.setFont("Helvetica", 9)
    canvas_obj.setFillColor(BRAND_GREEN_TINT)
    canvas_obj.drawString(MARGIN, PAGE_H - 0.70 * inch, "Automated Travel & Expense Reporting")

    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(BRAND_GREEN_TINT)
    canvas_obj.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.48 * inch, "AGENTIC AI EXPENSE PIPELINE")
    canvas_obj.setFont("Helvetica-Oblique", 8)
    canvas_obj.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.70 * inch,
                                datetime.now().strftime("%d %b %Y"))
    canvas_obj.restoreState()


class _NumberedCanvas(pdfcanvas.Canvas):
    """Defers drawing the footer until the total page count is known, so it
    can say 'Page N of M' instead of just 'Page N'. Standard reportlab
    recipe: buffer every page, then stamp each one once `save()` is called."""

    def __init__(self, *args, **kwargs):
        pdfcanvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(total_pages)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def _draw_footer(self, total_pages):
        self.saveState()
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.6)
        self.line(MARGIN, 0.62 * inch, PAGE_W - MARGIN, 0.62 * inch)
        self.setFont("Helvetica", 8)
        self.setFillColor(TEXT_MUTED)
        self.drawString(MARGIN, 0.45 * inch,
                         "Confidential — generated automatically by ExpenseFlow AI. For internal use only.")
        self.drawRightString(PAGE_W - MARGIN, 0.45 * inch,
                              f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()


def generate_pdf_report(state: ExpenseReportState, run_id: str) -> str:
    reports_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"Expense_Report_{run_id}.pdf"
    filepath = os.path.join(reports_dir, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=letter,
        topMargin=1.3 * inch, bottomMargin=0.9 * inch,
        leftMargin=MARGIN, rightMargin=MARGIN,
        title="ExpenseFlow AI Report",
    )
    styles = _styles()
    story = []

    is_reimbursement = state.reimbursement is not None
    doc_title = "Reimbursement Statement" if is_reimbursement else "Expense Report"

    period = "Unknown"
    if state.date_range:
        period = state.date_range.start_date.strftime('%B %Y')

    # ── Title block ──────────────────────────────────────────────────────
    story.append(Paragraph(doc_title, styles["DocTitle"]))
    story.append(Spacer(1, 6))
    meta = [
        [Paragraph("PREPARED FOR", styles["MetaLabel"]), Paragraph(escape(state.user_id), styles["MetaValue"]),
         Paragraph("REPORTING PERIOD", styles["MetaLabel"]), Paragraph(escape(period), styles["MetaValue"])],
        [Paragraph("REFERENCE", styles["MetaLabel"]), Paragraph(escape(str(run_id)), styles["MetaValue"]),
         Paragraph("GENERATED ON", styles["MetaLabel"]), Paragraph(datetime.now().strftime('%d %b %Y, %H:%M'), styles["MetaValue"])],
    ]
    meta_table = Table(meta, colWidths=[1.3 * inch, 2.15 * inch, 1.3 * inch, 2.15 * inch])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 14))

    # ── Executive summary ────────────────────────────────────────────────
    story.append(_section_heading("Executive Summary", styles))

    confirmed_total = state.totals.get('confirmed_total', 0.0)
    provisional_total = state.provisional_totals.get('provisional_total', 0.0)
    review_count = len([f for f in state.missing_data_flags if f.status == 'NEEDS_REVIEW'])

    stat_rows = [
        ["Confirmed Total", f"INR {confirmed_total:,.2f}"],
        ["Provisional Total", f"INR {provisional_total:,.2f}"],
        ["Number of Expenses", str(len(state.filtered_expenses))],
        ["Number Requiring Review", str(review_count)],
    ]
    stat_table = Table(stat_rows, colWidths=[2.6 * inch, 3.1 * inch])
    stat_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_MUTED),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_DARK),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, BRAND_GREEN_LIGHT]),
        ('BOX', (0, 0), (-1, -1), 0.6, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(stat_table)
    story.append(Spacer(1, 16))

    # ── Needs review ──────────────────────────────────────────────────────
    if state.missing_data_flags:
        review_data = [["Expense ID", "Problem", "Resolution / Required Action"]]
        for flag in state.missing_data_flags:
            if flag.status == "NEEDS_REVIEW":
                review_data.append([flag.expense_id, flag.problem, flag.action_required])

        if len(review_data) > 1:
            story.append(_section_heading("Needs Review", styles))
            t = Table(review_data, colWidths=[1.3 * inch, 1.9 * inch, 2.5 * inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 16))

    # ── Reimbursement decisions ──────────────────────────────────────────
    if state.reimbursement:
        from app.services.reimbursement import summary
        sheet = state.reimbursement
        totals = summary(sheet)

        story.append(_section_heading("Reimbursement Decisions", styles))
        story.append(Paragraph(
            f"Meal cap per claim: INR {sheet['meal_cap']}. Open exceptions: {totals['held']}",
            styles["Body"]))
        story.append(Spacer(1, 2))
        for key in ("claimed", "approved", "difference"):
            story.append(Paragraph(f"{key.title()} (INR): {totals[key] / 100:.2f}", styles["Body"]))
        story.append(Spacer(1, 10))

        for item in sheet["items"]:
            bg, ink = STATUS_COLORS.get(item["status"], (NEUTRAL_LIGHT, TEXT_MUTED))
            heading_table = Table(
                [[Paragraph(escape(f"{item['id']}  |  {item['merchant']}"), styles["ClaimTitle"]),
                  Paragraph(escape(item['status'].upper()), styles["ClaimBadge"])]],
                colWidths=[4.6 * inch, 1.15 * inch],
            )
            heading_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg),
                ('TEXTCOLOR', (1, 0), (1, 0), ink),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('BOX', (0, 0), (-1, -1), 0.6, BORDER),
            ]))

            receipt = item["evidence"] or {}
            evidence_amount = receipt.get("amount")
            receipt_total = "unavailable" if evidence_amount is None else f"INR {evidence_amount / 100:.2f}"
            claimed = "unavailable" if item["claimed"] is None else f"{item['currency']} {item['claimed'] / 100:.2f}"
            details = [f"Claim {claimed}. Receipt {receipt_total}. Approved INR {item['approved'] / 100:.2f}.",
                       item["reason"]]
            details.extend(f"{event['action'].title()}: {event['note']}" for event in item["events"] if event["note"])
            if decision := item.get("agent_review"):
                details.extend([f"Exception Resolution Agent: {decision['action']}",
                                f"Evidence Reviewer: {decision['verification']}"])

            body_paragraphs = [Spacer(1, 3)] + [Paragraph(escape(d), styles["Body"]) for d in details]
            story.append(KeepTogether([heading_table] + body_paragraphs))
            story.append(Spacer(1, 10))

    doc.build(story, onFirstPage=_draw_letterhead, onLaterPages=_draw_letterhead, canvasmaker=_NumberedCanvas)
    return filepath
