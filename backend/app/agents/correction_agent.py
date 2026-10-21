"""
Correction Agent: Handles recalculation and revalidation after review findings.
Receives structured correction requests from the Review Agent and applies fixes.
"""
from decimal import Decimal
from datetime import datetime
from app.state.blackboard import (
    ExpenseReportState, AgentMessage, DataQualityFlag
)


def correction_node(state: ExpenseReportState) -> ExpenseReportState:
    """
    Process correction requests from the Review Agent.
    - Re-runs calculation for total mismatches
    - Flags missing-field expenses
    - Removes excluded duplicates from categorized expenses
    """
    state.current_agent = "Correction"
    state.agent_status["Correction"] = "RUNNING"

    if not state.review_result or not state.review_result.findings:
        state.agent_status["Correction"] = "COMPLETED"
        state.run_log.append({
            "agent": "Correction",
            "action": "No corrections needed",
            "status": "COMPLETED",
        })
        return state

    corrections_applied = 0
    critical_unresolved = 0

    for finding in state.review_result.findings:
        if finding.resolution_status == "resolved":
            continue

        if finding.finding_type == "total_mismatch" and finding.severity == "critical":
            # Recalculate totals from scratch
            _recalculate_totals(state)
            finding.resolution_status = "resolved"
            corrections_applied += 1

            # Send correction result message
            msg = AgentMessage(
                sender="Correction",
                recipient="Expense Review",
                message_type="correction_result",
                status="resolved",
                findings=[{
                    "original_finding": finding.finding_type,
                    "action_taken": "Recalculated confirmed total from eligible expenses",
                    "new_confirmed_total": state.totals.get("confirmed_total", 0.0),
                }],
            )
            state.agent_messages.append(msg)

        elif finding.finding_type == "duplicate_included":
            # Remove excluded duplicates from categorized expenses
            excluded_ids = {f.expense_id for f in state.missing_data_flags if f.status == "EXCLUDED"}
            state.categorized_expenses = [
                e for e in state.categorized_expenses if e.id not in excluded_ids
            ]
            _recalculate_totals(state)
            finding.resolution_status = "resolved"
            corrections_applied += 1

            msg = AgentMessage(
                sender="Correction",
                recipient="Expense Review",
                message_type="correction_result",
                status="resolved",
                findings=[{
                    "original_finding": finding.finding_type,
                    "action_taken": "Removed excluded duplicates and recalculated",
                }],
            )
            state.agent_messages.append(msg)

        elif finding.finding_type == "missing_field_unflagged":
            # Flag the expense
            for exp_id in finding.affected_expense_ids:
                already_flagged = any(
                    f.expense_id == exp_id for f in state.missing_data_flags
                )
                if not already_flagged:
                    state.missing_data_flags.append(DataQualityFlag(
                        expense_id=exp_id,
                        problem="Missing field (flagged by Review Agent)",
                        action_required="Provide missing data",
                        status="NEEDS_REVIEW",
                    ))
            _recalculate_totals(state)
            finding.resolution_status = "resolved"
            corrections_applied += 1

        elif finding.finding_type == "category_mismatch":
            # Category subtotals are derived from recalculation
            _recalculate_totals(state)
            finding.resolution_status = "resolved"
            corrections_applied += 1

        elif finding.finding_type == "report_inconsistency":
            # Cannot fix report generation — escalate
            finding.resolution_status = "escalated"
            critical_unresolved += 1

        else:
            # Unknown finding type — escalate
            finding.resolution_status = "escalated"
            critical_unresolved += 1

    # Determine if escalation is needed
    if critical_unresolved > 0:
        state.needs_human_review = True

    # Clear the inject flag after correction (so re-review sees clean state)
    state.inject_discrepancy = False
    state.retry_count += 1

    state.agent_status["Correction"] = "COMPLETED"
    state.run_log.append({
        "agent": "Correction",
        "action": (
            f"Applied {corrections_applied} correction(s), "
            f"{critical_unresolved} escalated to human review"
        ),
        "status": "COMPLETED",
    })

    return state


def _recalculate_totals(state: ExpenseReportState):
    """Deterministically recalculate totals from categorized expenses."""
    flagged_ids = {
        f.expense_id for f in state.missing_data_flags
        if f.status == "NEEDS_REVIEW"
    }

    confirmed_total = Decimal("0.00")
    provisional_total = Decimal("0.00")
    subtotals = {}

    for exp in state.categorized_expenses:
        amount = Decimal(str(exp.amount)) if exp.amount is not None else Decimal("0.00")
        if exp.id in flagged_ids:
            provisional_total += amount
        else:
            confirmed_total += amount
            subtotals[exp.category] = subtotals.get(exp.category, Decimal("0.00")) + amount

    state.totals = {"confirmed_total": float(confirmed_total)}
    for k, v in subtotals.items():
        state.totals[k] = float(v)

    state.provisional_totals = {"provisional_total": float(provisional_total)}
