"""Anomaly Detection Agent (Unit II: Planning & Reasoning).

Runs only when the Orchestrator's planner detected a threshold request
(e.g. "flag anything over 5000"). Flags categorized expenses whose amount
exceeds that threshold; it never changes totals or categories, so the
Expense Review Agent's independent recalculation is unaffected.
"""
from app.state.blackboard import ExpenseReportState


def anomaly_detection_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Anomaly Detection"

    threshold = state.intent.anomaly_threshold if state.intent else None
    if threshold is None:
        state.agent_status["Anomaly Detection"] = "SKIPPED"
        state.run_log.append({
            "agent": "Anomaly Detection",
            "action": "Not requested in the user's prompt; stage skipped.",
            "status": "SKIPPED",
        })
        return state

    state.agent_status["Anomaly Detection"] = "RUNNING"

    flagged_ids = []
    for exp in state.categorized_expenses:
        if exp.amount is not None and exp.amount > threshold:
            exp.is_anomaly = True
            flagged_ids.append(exp.id)

    state.agent_status["Anomaly Detection"] = "COMPLETED"
    state.run_log.append({
        "agent": "Anomaly Detection",
        "action": (
            f"Flagged {len(flagged_ids)} expense(s) above {threshold}: "
            f"{', '.join(flagged_ids) if flagged_ids else 'none'}"
        ),
        "status": "COMPLETED",
    })
    return state
