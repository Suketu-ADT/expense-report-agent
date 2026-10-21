import pytest
from datetime import date
from decimal import Decimal

from app.state.blackboard import (
    ExpenseReportState, Expense, CategorizedExpense, DataQualityFlag,
    DateRange, ReviewResult, ReviewFinding, AgentMessage
)
from app.agents.review_agent import review_node
from app.agents.correction_agent import correction_node
from app.agents.calculation_agent import calculation_node
from app.graph.expense_graph import check_review, check_after_persist


def test_4_expense_total_reconciliation():
    """Test 4: Expense Review Agent reconciles confirmed totals with categorized expenses."""
    state = ExpenseReportState(user_id="test_user")
    state.categorized_expenses = [
        CategorizedExpense(id="1", date=date(2026, 6, 10), merchant="Airline", amount=1500.0, currency="INR", category="Airfare"),
        CategorizedExpense(id="2", date=date(2026, 6, 12), merchant="Hotel", amount=2500.0, currency="INR", category="Lodging"),
    ]
    # Correct calculation totals
    state.totals = {"confirmed_total": 4000.0, "Airfare": 1500.0, "Lodging": 2500.0}
    state.provisional_totals = {"provisional_total": 0.0}

    state = review_node(state)
    assert state.review_result.overall_status == "passed"
    assert len(state.review_result.findings) == 0


def test_5_duplicate_transaction_handling():
    """Test 5: Review Agent detects duplicate transaction included in categorized expenses."""
    state = ExpenseReportState(user_id="test_user")
    state.missing_data_flags = [
        DataQualityFlag(expense_id="dup-2", problem="Duplicate", action_required="Excluded", status="EXCLUDED")
    ]
    # Faulty pipeline: dup-2 was mistakenly left in categorized_expenses
    state.categorized_expenses = [
        CategorizedExpense(id="1", date=date(2026, 6, 10), merchant="IndiGo", amount=1000.0, currency="INR", category="Airfare"),
        CategorizedExpense(id="dup-2", date=date(2026, 6, 10), merchant="IndiGo", amount=1000.0, currency="INR", category="Airfare"),
    ]
    state.totals = {"confirmed_total": 2000.0, "Airfare": 2000.0}
    state.provisional_totals = {"provisional_total": 0.0}

    state = review_node(state)
    assert state.review_result.overall_status == "needs_correction"
    dup_findings = [f for f in state.review_result.findings if f.finding_type == "duplicate_included"]
    assert len(dup_findings) == 1
    assert dup_findings[0].severity == "critical"
    assert dup_findings[0].affected_expense_ids == ["dup-2"]


def test_6_missing_field_review_behavior():
    """Test 6: Review Agent detects unflagged missing fields."""
    state = ExpenseReportState(user_id="test_user")
    state.categorized_expenses = [
        CategorizedExpense(id="exp-no-amt", date=date(2026, 6, 10), merchant="Unknown", amount=None, currency="INR", category="Meals")
    ]
    state.totals = {"confirmed_total": 0.0}
    state.provisional_totals = {"provisional_total": 0.0}

    state = review_node(state)
    missing_findings = [f for f in state.review_result.findings if f.finding_type == "missing_field_unflagged"]
    assert len(missing_findings) == 1
    assert "exp-no-amt" in missing_findings[0].affected_expense_ids


def test_7_structured_agent_communication():
    """Test 7: Review Agent creates structured AgentMessage objects for responsible agents."""
    state = ExpenseReportState(user_id="test_user")
    state.categorized_expenses = [
        CategorizedExpense(id="1", date=date(2026, 6, 10), merchant="A", amount=500.0, currency="INR", category="Meals")
    ]
    # Introduce discrepancy: reported total is wrong
    state.totals = {"confirmed_total": 999.0, "Meals": 500.0}
    state.provisional_totals = {"provisional_total": 0.0}

    state = review_node(state)
    assert len(state.agent_messages) >= 1
    msg = state.agent_messages[0]
    assert isinstance(msg, AgentMessage)
    assert msg.sender == "Expense Review"
    assert msg.recipient == "Calculation"
    assert msg.message_type == "correction_request"
    assert msg.status == "sent"
    assert msg.requested_action is not None


def test_8_discrepancy_injection_and_detection():
    """Test 8: Controlled test discrepancy injection is detected by Review Agent."""
    state = ExpenseReportState(user_id="test_user", inject_discrepancy=True)
    state.categorized_expenses = [
        CategorizedExpense(id="1", date=date(2026, 6, 10), merchant="Flight", amount=2000.0, currency="INR", category="Airfare")
    ]
    state.totals = {"confirmed_total": 2000.0, "Airfare": 2000.0}
    state.provisional_totals = {"provisional_total": 0.0}

    state = review_node(state)
    assert state.review_result.overall_status == "needs_correction"
    mismatch_findings = [f for f in state.review_result.findings if f.finding_type == "total_mismatch"]
    assert len(mismatch_findings) >= 1
    assert mismatch_findings[0].severity == "critical"


def test_9_conditional_retry_and_recovery():
    """Test 9: Correction Agent successfully recovers from Review Agent findings."""
    state = ExpenseReportState(user_id="test_user", inject_discrepancy=True)
    state.categorized_expenses = [
        CategorizedExpense(id="1", date=date(2026, 6, 10), merchant="Hotel", amount=3000.0, currency="INR", category="Lodging")
    ]
    state.totals = {"confirmed_total": 3000.0, "Lodging": 3000.0}
    state.provisional_totals = {"provisional_total": 0.0}

    # Step A: Review detects injected error
    state = review_node(state)
    assert state.review_result.overall_status == "needs_correction"

    # Step B: Graph routing check
    route = check_review(state)
    assert route == "correction"

    # Step C: Correction node fixes the discrepancy
    state = correction_node(state)
    assert state.agent_status["Correction"] == "COMPLETED"
    assert state.totals["confirmed_total"] == 3000.0

    # Step D: Re-review pass (inject_discrepancy is now False)
    state = review_node(state)
    assert state.review_result.overall_status == "passed"
    route_after = check_review(state)
    assert route_after == "report"


def test_10_maximum_retry_limit_and_escalation():
    """Test 10: Exceeding max_retries triggers human escalation."""
    state = ExpenseReportState(user_id="test_user")
    state.review_result = ReviewResult(
        overall_status="needs_correction",
        findings=[ReviewFinding(
            finding_type="total_mismatch",
            severity="critical",
            description="Persistent error",
            responsible_agent="Calculation",
        )]
    )
    state.retry_count = 3
    state.max_retries = 3

    route = check_review(state)
    assert state.needs_human_review is True
    assert route == "report"  # Escalates to human review while proceeding to generate flagged report


def test_11_escalation_when_correction_fails():
    """Test 11: Unfixable issue in Correction Agent triggers needs_human_review."""
    state = ExpenseReportState(user_id="test_user")
    state.review_result = ReviewResult(
        overall_status="needs_correction",
        findings=[ReviewFinding(
            finding_type="report_inconsistency",  # Cannot be auto-fixed by recalculation
            severity="critical",
            description="Missing PDF file",
            responsible_agent="Report Generation",
        )]
    )

    state = correction_node(state)
    assert state.needs_human_review is True


def test_12_and_13_prevention_of_dispatch_without_approval():
    """Test 12 & 13: Reports with needs_human_review or rejected status are held from email dispatch."""
    # Scenario A: Needs human review -> email held
    state_held = ExpenseReportState(user_id="test_user", needs_human_review=True)
    next_node = check_after_persist(state_held)
    assert next_node == "end"  # Blocked from email dispatch

    # Scenario B: Rejected status -> email held
    state_rejected = ExpenseReportState(user_id="test_user", approval_status="rejected")
    next_node_rej = check_after_persist(state_rejected)
    assert next_node_rej == "end"

    # Scenario C: Approval pending -> email held at approval gate
    state_pending = ExpenseReportState(user_id="test_user", needs_human_review=False, approval_status="pending")
    next_node_pending = check_after_persist(state_pending)
    assert next_node_pending == "end"
    assert state_pending.agent_status.get("Email Dispatch") == "WAITING"

    # Scenario D: Explicit approval granted -> email permitted
    state_approved = ExpenseReportState(user_id="test_user", needs_human_review=False, approval_status="approved")
    next_node_approved = check_after_persist(state_approved)
    assert next_node_approved == "email"


def test_14_prevention_of_duplicate_dispatch_during_retries():
    """Test 14: Ensure email is only dispatched after final review pass, not during retries."""
    # During review failure, graph routes to 'correction', NOT 'email' or 'report'
    state = ExpenseReportState(user_id="test_user", retry_count=0, max_retries=3)
    state.review_result = ReviewResult(overall_status="needs_correction", findings=[
        ReviewFinding(finding_type="total_mismatch", severity="critical", description="err", responsible_agent="Calculation")
    ])
    assert check_review(state) == "correction"
    # Delivery status remains pending
    assert state.delivery_status == "pending"
