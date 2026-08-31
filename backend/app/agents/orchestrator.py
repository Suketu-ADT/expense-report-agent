import re
from datetime import date, timedelta
import calendar
from app.state.blackboard import ExpenseReportState, DateRange

def resolve_last_month(current_date: date) -> DateRange:
    first_day_of_current = current_date.replace(day=1)
    last_day_of_previous = first_day_of_current - timedelta(days=1)
    first_day_of_previous = last_day_of_previous.replace(day=1)
    return DateRange(start_date=first_day_of_previous, end_date=last_day_of_previous)

def orchestrator_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Orchestrator"
    state.agent_status["Orchestrator"] = "RUNNING"
    
    # Fake parsing the request text, focusing on "last month"
    # The requirement uses August 31 2026 as the current date for the demo
    system_date = date(2026, 8, 31) 
    
    # In a real app, you'd extract the recipient and date intent from the text via LLM
    # For now, deterministic fallback for "last month"
    state.date_range = resolve_last_month(system_date)
    
    state.execution_plan = [
        "Data Retrieval",
        "Filter & Validation",
        "Categorization",
        "Calculation",
        "Report Generation",
        "Email Dispatch"
    ]
    
    state.agent_status["Orchestrator"] = "COMPLETED"
    state.run_log.append({"agent": "Orchestrator", "action": "Resolved last month", "status": "COMPLETED"})
    return state
