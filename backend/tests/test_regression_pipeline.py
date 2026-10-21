import pytest
import os
import tempfile
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.state.blackboard import ExpenseReportState, Expense, DateRange, ReviewResult, ReviewFinding
from app.graph.expense_graph import expense_graph, check_validation, check_review, check_after_persist
from app.agents.retrieval_agent import retrieval_node
from app.agents.validation_agent import validation_node
from app.agents.categorization_agent import categorization_node
from app.agents.calculation_agent import calculation_node
from app.agents.review_agent import review_node
from app.agents.correction_agent import correction_node
from app.agents.memory_agent import persist_memory_node
from app.services.memory_service import save_report_summary, get_all_reports, get_reports_by_period


@pytest.fixture
def isolated_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_normal_report_runs_beyond_validation_and_completes():
    """Verify that a normal report executes beyond validation all the way to memory persistence."""
    state = ExpenseReportState(
        user_id="test_user",
        request_text="Generate my travel expense report for July 2026 and email it to finance.",
        run_id="run-regress-01"
    )

    final_state = None
    for event in expense_graph.stream(state, stream_mode="values"):
        final_state = ExpenseReportState(**event) if isinstance(event, dict) else event

    assert final_state is not None
    # All nodes up to memory persistence must be completed
    assert final_state.agent_status.get("Orchestrator") == "COMPLETED"
    assert final_state.agent_status.get("Data Retrieval") == "COMPLETED"
    assert final_state.agent_status.get("Filter & Validation") == "COMPLETED"
    assert final_state.agent_status.get("Categorization") == "COMPLETED"
    assert final_state.agent_status.get("Calculation") == "COMPLETED"
    assert final_state.agent_status.get("Expense Review") == "COMPLETED"
    assert final_state.agent_status.get("Report Generation") == "COMPLETED"
    assert final_state.agent_status.get("Memory Persistence") == "COMPLETED"
    # Email dispatch waits for human approval gate
    assert final_state.agent_status.get("Email Dispatch") == "WAITING"
    assert len(final_state.filtered_expenses) > 0
    assert final_state.totals.get("confirmed_total", 0.0) > 0.0


def test_valid_records_not_all_discarded_due_to_missing_date_or_duplicate():
    """Verify missing dates are preserved as provisional items and duplicates excluded without discarding valid records."""
    state = ExpenseReportState(
        user_id="test_user",
        date_range=DateRange(start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))
    )
    # Load actual sample dataset
    state = retrieval_node(state)
    assert len(state.raw_expenses) == 10

    state = validation_node(state)
    # 8 confirmed valid + 1 missing date flagged = 9 filtered expenses (1 duplicate excluded)
    assert len(state.filtered_expenses) == 9

    # Check missing date flag exists
    missing_date_flags = [f for f in state.missing_data_flags if f.problem == "Missing date"]
    assert len(missing_date_flags) == 1
    assert missing_date_flags[0].expense_id == "EXP-7003"
    assert missing_date_flags[0].status == "NEEDS_REVIEW"

    # Check duplicate flag exists and is excluded
    dup_flags = [f for f in state.missing_data_flags if f.problem == "Duplicate"]
    assert len(dup_flags) == 1
    assert dup_flags[0].expense_id == "EXP-7005"
    assert dup_flags[0].status == "EXCLUDED"


def test_categorization_and_calculation_execution():
    """Categorization assigns proper categories and Calculation computes confirmed and provisional totals."""
    state = ExpenseReportState(
        user_id="test_user",
        date_range=DateRange(start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))
    )
    state = retrieval_node(state)
    state = validation_node(state)
    state = categorization_node(state)
    state = calculation_node(state)

    assert state.agent_status.get("Categorization") == "COMPLETED"
    assert state.agent_status.get("Calculation") == "COMPLETED"
    # Confirmed: EXP-7001 (8450) + 7002 (12000) + 7004 (480) + 7006 (1350) + 7007 (200) + 7008 (2100) + 7009 (5200) + 7010 (9500) = 39280.0
    assert state.totals["confirmed_total"] == 39280.0
    # Provisional: EXP-7003 (650)
    assert state.provisional_totals["provisional_total"] == 650.0
    # Categories
    assert state.totals["Airfare"] == 13650.0
    assert state.totals["Lodging"] == 21500.0
    assert state.totals["Meals"] == 3450.0
    assert state.totals["Ground Transport"] == 680.0


def test_expense_review_executes_after_calculation():
    """Expense Review executes independently after calculation and passes on clean data."""
    state = ExpenseReportState(
        user_id="test_user",
        date_range=DateRange(start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))
    )
    state = retrieval_node(state)
    state = validation_node(state)
    state = categorization_node(state)
    state = calculation_node(state)
    state = review_node(state)

    assert state.agent_status.get("Expense Review") == "COMPLETED"
    assert state.review_result is not None
    assert state.review_result.overall_status == "passed"
    assert len(state.review_result.findings) == 0


def test_injected_discrepancy_detected_and_corrected_via_recovery_loop():
    """When discrepancy is injected, Review detects it, emits message, Correction fixes it, and Re-Review passes."""
    state = ExpenseReportState(
        user_id="test_user",
        request_text="Generate my travel expense report for July 2026",
        inject_discrepancy=True,
        run_id="run-regress-inject"
    )

    final_state = None
    for event in expense_graph.stream(state, stream_mode="values"):
        final_state = ExpenseReportState(**event) if isinstance(event, dict) else event

    assert final_state is not None
    # Verify discrepancy recovery occurred
    assert final_state.retry_count == 1
    assert final_state.agent_status.get("Correction") == "COMPLETED"
    assert final_state.review_result is not None
    assert final_state.review_result.overall_status == "passed"
    # Inter-agent messages exchanged
    messages = final_state.agent_messages
    assert len(messages) >= 2
    correction_req = [m for m in messages if m.message_type == "correction_request"]
    correction_res = [m for m in messages if m.message_type == "correction_result"]
    assert len(correction_req) >= 1
    assert len(correction_res) >= 1
    assert correction_req[0].sender == "Expense Review"
    assert correction_req[0].recipient == "Calculation"
    assert correction_res[0].sender == "Correction"
    assert correction_res[0].recipient == "Expense Review"
    # Correct final totals restored
    assert final_state.totals["confirmed_total"] == 39280.0


def test_memory_persistence_idempotent_once_per_completed_run(isolated_db):
    """Memory persistence is idempotent: multiple saves for same run_id update the record instead of creating duplicates."""
    report_id1 = save_report_summary(
        run_id="run-unique-123",
        user_id="alice",
        period_start="2026-07-01",
        period_end="2026-07-31",
        period_label="July 2026",
        confirmed_total=39280.0,
        provisional_total=650.0,
        category_totals={"Airfare": 13650.0},
        total_expenses=9,
        flagged_count=1,
        excluded_count=1,
        review_status="passed",
        review_findings=[],
        db=isolated_db
    )

    # Re-saving same run_id (e.g. on retry or re-execution)
    report_id2 = save_report_summary(
        run_id="run-unique-123",
        user_id="alice",
        period_start="2026-07-01",
        period_end="2026-07-31",
        period_label="July 2026",
        confirmed_total=39280.0,
        provisional_total=650.0,
        category_totals={"Airfare": 13650.0},
        total_expenses=9,
        flagged_count=1,
        excluded_count=1,
        review_status="passed",
        review_findings=[],
        db=isolated_db
    )

    assert report_id1 == report_id2
    reports = get_reports_by_period("July 2026", user_id="alice", db=isolated_db)
    assert len(reports) == 1


def test_approval_required_before_external_email_dispatch():
    """Verify that email dispatch cannot occur without explicit human approval."""
    # Pending approval -> blocked
    state_pending = ExpenseReportState(
        user_id="test_user",
        approval_status="pending",
        needs_human_review=False
    )
    assert check_after_persist(state_pending) == "end"
    assert state_pending.agent_status.get("Email Dispatch") == "WAITING"

    # Needs human review -> blocked
    state_review = ExpenseReportState(
        user_id="test_user",
        approval_status="pending",
        needs_human_review=True
    )
    assert check_after_persist(state_review) == "end"

    # Explicitly approved -> permitted
    state_approved = ExpenseReportState(
        user_id="test_user",
        approval_status="approved",
        needs_human_review=False
    )
    assert check_after_persist(state_approved) == "email"


def test_period_adaptation_when_prompt_specifies_mismatched_month():
    """When user requests June 2026 but uploaded dataset only has July 2026 records, validation adapts rather than discarding all records."""
    state = ExpenseReportState(
        user_id="test_user",
        request_text="Generate my travel expense report for June 2026 and email it to finance."
    )
    # Orchestrator resolves to June 2026 initially
    from app.agents.orchestrator import orchestrator_node
    state = orchestrator_node(state)
    assert state.date_range.start_date.month == 6

    # Data Retrieval loads July 2026 records
    state = retrieval_node(state)

    # Filter & Validation adapts period to July 2026 so records are preserved
    state = validation_node(state)
    assert state.date_range.start_date.month == 7
    assert len(state.filtered_expenses) == 9
