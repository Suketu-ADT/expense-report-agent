"""
Memory Persistence Node: Saves report summary to persistent storage after report generation.
Part of Unit III — Long-term persistent memory.
"""
from app.state.blackboard import ExpenseReportState
from app.services.memory_service import save_report_summary


def persist_memory_node(state: ExpenseReportState, db=None) -> ExpenseReportState:
    """Save the completed report summary to SQLite for long-term memory."""
    state.current_agent = "Memory Persistence"
    state.agent_status["Memory Persistence"] = "RUNNING"

    try:
        period_start = ""
        period_end = ""
        period_label = "Unknown"

        if state.date_range:
            period_start = state.date_range.start_date.isoformat()
            period_end = state.date_range.end_date.isoformat()
            period_label = state.date_range.start_date.strftime("%B %Y")

        # Gather review info
        review_status = "pending"
        review_findings_data = []
        if state.review_result:
            review_status = state.review_result.overall_status
            review_findings_data = [f.model_dump() for f in state.review_result.findings]

        # Category totals (exclude confirmed_total key)
        category_totals = {
            k: v for k, v in state.totals.items() if k != "confirmed_total"
        }

        flagged_count = len([
            f for f in state.missing_data_flags if f.status == "NEEDS_REVIEW"
        ])
        excluded_count = len([
            f for f in state.missing_data_flags if f.status == "EXCLUDED"
        ])

        report_id = save_report_summary(
            run_id=state.run_id or "unknown",
            user_id=state.user_id,
            period_start=period_start,
            period_end=period_end,
            period_label=period_label,
            confirmed_total=state.totals.get("confirmed_total", 0.0),
            provisional_total=state.provisional_totals.get("provisional_total", 0.0),
            category_totals=category_totals,
            total_expenses=len(state.filtered_expenses),
            flagged_count=flagged_count,
            excluded_count=excluded_count,
            review_status=review_status,
            review_findings=review_findings_data,
            report_file_path=state.report_file,
            delivery_status=state.delivery_status,
            db=db,
        )

        state.report_id = report_id

        state.agent_status["Memory Persistence"] = "COMPLETED"
        if state.approval_status != "approved":
            state.agent_status["Email Dispatch"] = "WAITING"

        state.run_log.append({
            "agent": "Memory Persistence",
            "action": f"Report saved as {report_id}",
            "status": "COMPLETED",
        })
    except Exception as e:
        state.agent_status["Memory Persistence"] = "FAILED"
        state.errors.append(f"Memory persistence failed: {e}")
        state.run_log.append({
            "agent": "Memory Persistence",
            "action": "Save report summary",
            "status": "FAILED",
            "error": str(e),
        })

    return state
