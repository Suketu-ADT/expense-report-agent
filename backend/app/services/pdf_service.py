from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
from datetime import datetime
from app.state.blackboard import ExpenseReportState

def generate_pdf_report(state: ExpenseReportState, run_id: str) -> str:
    reports_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    filename = f"Expense_Report_{run_id}.pdf"
    filepath = os.path.join(reports_dir, filename)
    
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Header
    story.append(Paragraph("EXPENSE REPORT", styles['Title']))
    story.append(Paragraph(f"User: {state.user_id}", styles['Normal']))
    
    period = "Unknown"
    if state.date_range:
        period = f"{state.date_range.start_date.strftime('%B %Y')}"
        
    story.append(Paragraph(f"Reporting Period: {period}", styles['Normal']))
    story.append(Paragraph(f"Generated Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Executive Summary
    story.append(Paragraph("EXECUTIVE SUMMARY", styles['Heading2']))
    
    confirmed_total = state.totals.get('confirmed_total', 0.0)
    provisional_total = state.provisional_totals.get('provisional_total', 0.0)
    
    story.append(Paragraph(f"Confirmed Total: {confirmed_total:.2f}", styles['Normal']))
    story.append(Paragraph(f"Provisional Total: {provisional_total:.2f}", styles['Normal']))
    story.append(Paragraph(f"Number of Expenses: {len(state.filtered_expenses)}", styles['Normal']))
    story.append(Paragraph(f"Number Requiring Review: {len([f for f in state.missing_data_flags if f.status == 'NEEDS_REVIEW'])}", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Needs Review
    if state.missing_data_flags:
        story.append(Paragraph("NEEDS REVIEW", styles['Heading2']))
        review_data = [["Expense ID", "Problem", "Resolution / Required Action"]]
        for flag in state.missing_data_flags:
            if flag.status == "NEEDS_REVIEW":
                review_data.append([flag.expense_id, flag.problem, flag.action_required])
        
        if len(review_data) > 1:
            t = Table(review_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))
    
    doc.build(story)
    return filepath
