from app.state.blackboard import ExpenseReportState
from app.services.email_service import send_email
from app.services.email_template import build_expense_report_html
import os

def email_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Email Dispatch"
    state.agent_status["Email Dispatch"] = "RUNNING"
    
    to_email = os.getenv("FINANCE_EMAIL", "finance@example.com")
    period = state.date_range.start_date.strftime('%B %Y') if state.date_range else "Unknown Period"
    subject = f"Travel Expense Report — {period}"
    
    confirmed = state.totals.get("confirmed_total", 0.0)
    provisional = state.provisional_totals.get("provisional_total", 0.0)
    needs_review = len([f for f in state.missing_data_flags if f.status == "NEEDS_REVIEW"])
    
    body = (
        f"Reporting Period: {period}\n"
        f"Confirmed Grand Total: {confirmed:.2f}\n"
    )
    if provisional > 0:
        body += f"Provisional Total: {provisional:.2f}\n"
        
    body += f"Number of items needing review: {needs_review}\n"
    
    # Rich HTML version (matches the dashboard's Expense Reports section); the
    # plain-text body above stays as the fallback for clients that cannot show HTML.
    html_body = build_expense_report_html(state)

    success = send_email(to_email, subject, body, state.report_file, html_body=html_body)
    
    if success:
        state.delivery_status = "delivered"
        state.agent_status["Email Dispatch"] = "COMPLETED"
        mode = "simulated" if os.getenv("DEVELOPMENT_MODE", "true").lower() == "true" else "sent"
        state.run_log.append({
            "agent": "Email Dispatch", 
            "action": f"Email {mode} successfully", 
            "status": "COMPLETED"
        })
    else:
        state.delivery_status = "failed"
        state.agent_status["Email Dispatch"] = "FAILED"
        state.errors.append("Failed to send email.")
        state.run_log.append({
            "agent": "Email Dispatch", 
            "action": "Send email", 
            "status": "FAILED",
            "error": "Failed to send email"
        })
        
    return state
