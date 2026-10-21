from langgraph.graph import StateGraph, END
from app.state.blackboard import ExpenseReportState
from app.agents.orchestrator import orchestrator_node
from app.agents.retrieval_agent import retrieval_node
from app.agents.validation_agent import validation_node
from app.agents.categorization_agent import categorization_node
from app.agents.calculation_agent import calculation_node
from app.agents.report_agent import report_node
from app.agents.email_agent import email_node
from app.agents.review_agent import review_node
from app.agents.correction_agent import correction_node
from app.agents.memory_agent import persist_memory_node

def check_retrieval(state: ExpenseReportState) -> str:
    if state.agent_status.get("Data Retrieval") == "FAILED":
        return "end"
    if not state.raw_expenses:
        state.run_log.append({"agent": "System", "action": "Zero expenses", "status": "COMPLETED"})
        return "end"
    return "validation"

def check_validation(state: ExpenseReportState) -> str:
    if not state.filtered_expenses:
        msg = "No valid expense records remained after Filter & Validation."
        state.errors.append(msg)
        for stage in [
            "Categorization", "Calculation", "Expense Review",
            "Correction", "Report Generation", "Memory Persistence", "Email Dispatch"
        ]:
            if stage not in state.agent_status:
                state.agent_status[stage] = "SKIPPED"
        state.run_log.append({
            "agent": "Filter & Validation",
            "action": f"Workflow halted: {msg}",
            "status": "FAILED",
            "error": msg,
        })
        return "end"
    return "categorization"

def check_review(state: ExpenseReportState) -> str:
    """Route based on review outcome: passed → report, needs_correction → correct, needs_human_review → escalate."""
    if state.review_result is None:
        return "report"

    if state.review_result.overall_status == "passed":
        return "report"
    elif state.review_result.overall_status == "needs_correction":
        if state.retry_count < state.max_retries:
            return "correction"
        else:
            # Max retries exceeded — escalate
            state.needs_human_review = True
            state.run_log.append({
                "agent": "System",
                "action": f"Max retries ({state.max_retries}) reached. Escalating to human review.",
                "status": "WARNING"
            })
            return "report"  # Still generate report but marked as needs review
    else:
        # needs_human_review
        state.needs_human_review = True
        return "report"

def check_after_correction(state: ExpenseReportState) -> str:
    """After correction, route to re-review."""
    return "re_review"

def check_report(state: ExpenseReportState) -> str:
    if state.agent_status.get("Report Generation") == "FAILED":
        return "end"
    return "persist_memory"

def check_after_persist(state: ExpenseReportState) -> str:
    """After persisting memory, check if email should be sent (requires explicit approval)."""
    # Block email if report needs human review
    if state.needs_human_review:
        state.agent_status["Email Dispatch"] = "WAITING"
        state.run_log.append({
            "agent": "System",
            "action": "Email held: report requires human review before dispatch",
            "status": "WARNING"
        })
        return "end"

    # Block email if rejected
    if state.approval_status == "rejected":
        state.agent_status["Email Dispatch"] = "FAILED"
        state.run_log.append({
            "agent": "System",
            "action": "Email cancelled: report was rejected by reviewer",
            "status": "WARNING"
        })
        return "end"

    # Enforce explicit approval gate
    if state.approval_status != "approved":
        state.agent_status["Email Dispatch"] = "WAITING"
        state.run_log.append({
            "agent": "System",
            "action": "Email held: awaiting explicit human approval gate before dispatch",
            "status": "INFO"
        })
        return "end"

    return "email"

def check_email(state: ExpenseReportState) -> str:
    return "end"

def build_graph():
    builder = StateGraph(ExpenseReportState)

    # Add nodes
    builder.add_node("Orchestrator", orchestrator_node)
    builder.add_node("Data Retrieval", retrieval_node)
    builder.add_node("Filter & Validation", validation_node)
    builder.add_node("Categorization", categorization_node)
    builder.add_node("Calculation", calculation_node)
    builder.add_node("Expense Review", review_node)
    builder.add_node("Correction", correction_node)
    builder.add_node("Re-Review", review_node)   # Same review logic for re-review pass
    builder.add_node("Report Generation", report_node)
    builder.add_node("Memory Persistence", persist_memory_node)
    builder.add_node("Email Dispatch", email_node)

    # Add edges
    builder.set_entry_point("Orchestrator")
    builder.add_edge("Orchestrator", "Data Retrieval")

    builder.add_conditional_edges(
        "Data Retrieval",
        check_retrieval,
        {"validation": "Filter & Validation", "end": END}
    )

    builder.add_conditional_edges(
        "Filter & Validation",
        check_validation,
        {"categorization": "Categorization", "end": END}
    )

    builder.add_edge("Categorization", "Calculation")
    builder.add_edge("Calculation", "Expense Review")

    # Review → conditional routing
    builder.add_conditional_edges(
        "Expense Review",
        check_review,
        {"report": "Report Generation", "correction": "Correction"}
    )

    # Correction → re-review
    builder.add_conditional_edges(
        "Correction",
        check_after_correction,
        {"re_review": "Re-Review"}
    )

    # Re-Review → same routing as initial review
    builder.add_conditional_edges(
        "Re-Review",
        check_review,
        {"report": "Report Generation", "correction": "Correction"}
    )

    builder.add_conditional_edges(
        "Report Generation",
        check_report,
        {"persist_memory": "Memory Persistence", "end": END}
    )

    builder.add_conditional_edges(
        "Memory Persistence",
        check_after_persist,
        {"email": "Email Dispatch", "end": END}
    )

    builder.add_edge("Email Dispatch", END)

    return builder.compile()

expense_graph = build_graph()
