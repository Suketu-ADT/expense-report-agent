import re
from datetime import date, timedelta
import calendar
from app.state.blackboard import ExpenseReportState, DateRange
from app.services.memory_service import get_reports_by_period, get_user_preferences

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12
}

def resolve_last_month(current_date: date) -> DateRange:
    first_day_of_current = current_date.replace(day=1)
    last_day_of_previous = first_day_of_current - timedelta(days=1)
    first_day_of_previous = last_day_of_previous.replace(day=1)
    return DateRange(start_date=first_day_of_previous, end_date=last_day_of_previous)

def resolve_month_from_text(text: str) -> DateRange | None:
    """Try to extract a specific month+year from the request text."""
    # Match patterns like "June 2026", "june 2026", "Jun 2026"
    pattern = r'\b(' + '|'.join(MONTH_NAMES.keys()) + r')\s+(\d{4})\b'
    match = re.search(pattern, text.lower())
    if match:
        month = MONTH_NAMES[match.group(1)]
        year = int(match.group(2))
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        return DateRange(start_date=first_day, end_date=last_day)
    return None

def orchestrator_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Orchestrator"
    state.agent_status["Orchestrator"] = "RUNNING"
    
    system_date = date(2026, 8, 31)
    
    # Try to parse a specific month from the request text
    parsed_range = None
    if state.request_text:
        parsed_range = resolve_month_from_text(state.request_text)
    
    if parsed_range:
        state.date_range = parsed_range
        period_label = f"{state.date_range.start_date.strftime('%B %Y')}"
    else:
        # Fallback to "last month"
        state.date_range = resolve_last_month(system_date)
        period_label = "last month"
    
    state.execution_plan = [
        "Data Retrieval",
        "Filter & Validation",
        "Categorization",
        "Calculation",
        "Expense Review",
        "Report Generation",
        "Memory Persistence",
        "Email Dispatch"
    ]
    
    # ── Unit III: Memory Recall ─────────────────────────────────────────
    try:
        prior_reports = get_reports_by_period(period_label, user_id=state.user_id)
        prefs = get_user_preferences(state.user_id)
        state.historical_context = {
            "prior_reports_for_period": prior_reports,
            "prior_report_count": len(prior_reports),
            "user_preferences": prefs,
        }
        if prior_reports:
            state.run_log.append({
                "agent": "Orchestrator",
                "action": f"Memory recall: found {len(prior_reports)} prior report(s) for {period_label}",
                "status": "COMPLETED"
            })
        else:
            state.run_log.append({
                "agent": "Orchestrator",
                "action": f"Memory recall: no prior report for {period_label}",
                "status": "COMPLETED"
            })
    except Exception as e:
        state.historical_context = {"prior_report_count": 0, "error": str(e)}

    state.agent_status["Orchestrator"] = "COMPLETED"
    state.run_log.append({"agent": "Orchestrator", "action": f"Resolved period: {period_label}", "status": "COMPLETED"})
    return state
