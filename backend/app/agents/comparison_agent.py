"""Period Comparison Agent (Unit II: Planning & Reasoning; Unit III: Memory).

Runs only when the Orchestrator's planner detected a comparison request
(e.g. "compare to last month"). Recalls the previous period's confirmed
total from persistent memory (SQLite) and computes the delta against the
current run. It only reads memory and writes state.comparison — it never
touches totals or categorized_expenses, so the Expense Review Agent's
independent recalculation is unaffected.
"""
from datetime import timedelta

from app.state.blackboard import ExpenseReportState
from app.services.memory_service import get_reports_by_period


def _previous_period_label(date_range) -> str:
    if date_range is None:
        return ""
    first_day_of_current = date_range.start_date.replace(day=1)
    last_day_of_previous = first_day_of_current - timedelta(days=1)
    return last_day_of_previous.strftime("%B %Y")


def comparison_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Period Comparison"

    if not state.intent or not state.intent.compare_to_previous:
        state.agent_status["Period Comparison"] = "SKIPPED"
        state.run_log.append({
            "agent": "Period Comparison",
            "action": "Not requested in the user's prompt; stage skipped.",
            "status": "SKIPPED",
        })
        return state

    state.agent_status["Period Comparison"] = "RUNNING"

    prev_label = _previous_period_label(state.date_range)
    prior_reports = get_reports_by_period(prev_label, user_id=state.user_id) if prev_label else []
    current_total = state.totals.get("confirmed_total", 0.0)

    if prior_reports:
        previous_total = prior_reports[0]["confirmed_total"]
        delta = current_total - previous_total
        delta_pct = (delta / previous_total * 100) if previous_total else None
        state.comparison = {
            "available": True,
            "previous_period": prev_label,
            "previous_total": previous_total,
            "current_total": current_total,
            "delta": delta,
            "delta_pct": delta_pct,
        }
        action = (
            f"{prev_label}: ₹{previous_total:.2f} -> current ₹{current_total:.2f} "
            f"(Δ {delta:+.2f})"
        )
    else:
        state.comparison = {
            "available": False,
            "previous_period": prev_label,
            "current_total": current_total,
        }
        action = f"No saved report found for {prev_label}; comparison unavailable."

    state.agent_status["Period Comparison"] = "COMPLETED"
    state.run_log.append({"agent": "Period Comparison", "action": action, "status": "COMPLETED"})
    return state
