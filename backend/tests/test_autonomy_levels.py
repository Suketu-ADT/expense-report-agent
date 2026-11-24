from datetime import date

from app.state.blackboard import ExpenseReportState, CategorizedExpense, DateRange
from app.agents.orchestrator import orchestrator_node
from app.agents.review_agent import review_node
from app.graph.expense_graph import check_review


def test_orchestrator_sets_max_retries_from_autonomy_level():
    cautious = orchestrator_node(ExpenseReportState(user_id="t", autonomy_level="cautious"))
    co_pilot = orchestrator_node(ExpenseReportState(user_id="t", autonomy_level="co_pilot"))
    trusting = orchestrator_node(ExpenseReportState(user_id="t", autonomy_level="trusting"))
    assert cautious.max_retries == 0
    assert co_pilot.max_retries == 3
    assert trusting.max_retries == 5


def test_unknown_autonomy_level_defaults_to_co_pilot_limit():
    state = orchestrator_node(ExpenseReportState(user_id="t", autonomy_level="not-a-real-level"))
    assert state.max_retries == 3


def _state_with_warning_only_finding(autonomy_level):
    # A missing amount that isn't flagged yet is a warning-only finding
    # (missing_field_unflagged), never critical on its own.
    state = ExpenseReportState(user_id="t", autonomy_level=autonomy_level)
    state.categorized_expenses = [
        CategorizedExpense(id="1", date=date(2026, 7, 5), merchant="A", amount=None,
                            currency="INR", category="Meals"),
    ]
    state.totals = {"confirmed_total": 0.0}
    state.provisional_totals = {"provisional_total": 0.0}
    return state


def test_co_pilot_passes_silently_on_warning_only_findings():
    state = review_node(_state_with_warning_only_finding("co_pilot"))
    assert state.review_result.overall_status == "passed"
    assert state.needs_human_review is False


def test_cautious_escalates_even_on_warning_only_findings():
    state = review_node(_state_with_warning_only_finding("cautious"))
    assert state.review_result.overall_status == "needs_human_review"
    assert check_review(state) == "report"
    assert state.needs_human_review is True


def test_cautious_mode_skips_auto_correction_on_critical_findings():
    """max_retries=0 means check_review escalates a critical finding on the
    very first pass instead of attempting Correction at all."""
    state = ExpenseReportState(user_id="t", autonomy_level="cautious")
    state.categorized_expenses = [
        CategorizedExpense(id="1", date=date(2026, 7, 5), merchant="A", amount=500.0,
                            currency="INR", category="Meals"),
    ]
    state.totals = {"confirmed_total": 999.0, "Meals": 500.0}  # deliberately wrong
    state.provisional_totals = {"provisional_total": 0.0}
    state.max_retries = 0  # as the Orchestrator would set for "cautious"

    state = review_node(state)
    assert state.review_result.overall_status == "needs_correction"
    assert check_review(state) == "report"
    assert state.needs_human_review is True
