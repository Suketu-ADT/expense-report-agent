import pytest
import os
import tempfile
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.memory import ReportHistoryModel, AgentMessageModel, UserPreferenceModel
from app.services.memory_service import (
    save_report_summary, get_report_by_id, get_reports_by_period,
    get_all_reports, save_agent_message, get_agent_messages,
    save_user_preference, get_user_preferences
)
from app.state.blackboard import ExpenseReportState, DateRange, ReviewResult, ReviewFinding
from app.agents.memory_agent import persist_memory_node


@pytest.fixture
def test_db():
    """Create a temporary SQLite database for test isolation."""
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


def test_1_save_and_retrieve_persistent_memory(test_db):
    """Test 1: Saving and retrieving persistent memory record."""
    report_id = save_report_summary(
        run_id="run-101",
        user_id="alice",
        period_start="2026-06-01",
        period_end="2026-06-30",
        period_label="June 2026",
        confirmed_total=4500.50,
        provisional_total=500.00,
        category_totals={"Airfare": 3000.0, "Meals": 1500.50},
        total_expenses=8,
        flagged_count=1,
        excluded_count=1,
        review_status="passed",
        review_findings=[],
        report_file_path="/reports/expense_report_june_2026.pdf",
        delivery_status="delivered",
        db=test_db,
    )

    assert report_id.startswith("RPT-")
    retrieved = get_report_by_id(report_id, db=test_db)
    assert retrieved is not None
    assert retrieved["report_id"] == report_id
    assert retrieved["user_id"] == "alice"
    assert retrieved["period_label"] == "June 2026"
    assert retrieved["confirmed_total"] == 4500.50
    assert retrieved["category_totals"]["Airfare"] == 3000.0
    assert retrieved["delivery_status"] == "delivered"


def test_2_persistence_across_new_database_session(test_db):
    """Test 2: Memory persistence across a new database session (simulating backend restart)."""
    # Step A: Save in current session
    report_id = save_report_summary(
        run_id="run-restart-test",
        user_id="bob",
        period_start="2026-07-01",
        period_end="2026-07-31",
        period_label="July 2026",
        confirmed_total=1200.00,
        provisional_total=0.0,
        category_totals={"Meals": 1200.0},
        total_expenses=3,
        flagged_count=0,
        excluded_count=0,
        review_status="passed",
        review_findings=[],
        db=test_db,
    )

    # Step B: Close the session and open a brand new session from the same engine/file
    engine = test_db.get_bind()
    test_db.close()

    NewSession = sessionmaker(bind=engine)
    new_db = NewSession()

    try:
        reloaded = get_report_by_id(report_id, db=new_db)
        assert reloaded is not None
        assert reloaded["report_id"] == report_id
        assert reloaded["user_id"] == "bob"
        assert reloaded["confirmed_total"] == 1200.00
    finally:
        new_db.close()


def test_3_historical_retrieval_when_no_records_exist(test_db):
    """Test 3: Historical retrieval when no records exist returns empty cleanly."""
    reports = get_reports_by_period("January 2025", user_id="nonexistent_user", db=test_db)
    assert reports == []

    all_reports = get_all_reports(user_id="nonexistent_user", db=test_db)
    assert all_reports == []

    single = get_report_by_id("RPT-NONEXISTENT", db=test_db)
    assert single is None


def test_agent_message_audit_trail(test_db):
    """Test persistence of structured inter-agent messages."""
    msg_id = save_agent_message(
        run_id="run-msg-test",
        sender="Expense Review",
        recipient="Calculation",
        message_type="correction_request",
        status="sent",
        findings=[{"finding_type": "total_mismatch", "severity": "critical"}],
        requested_action="Recalculate confirmed total",
        db=test_db,
    )
    assert msg_id > 0

    messages = get_agent_messages("run-msg-test", db=test_db)
    assert len(messages) == 1
    assert messages[0]["sender"] == "Expense Review"
    assert messages[0]["recipient"] == "Calculation"
    assert messages[0]["requested_action"] == "Recalculate confirmed total"


def test_user_preferences_persistence(test_db):
    """Test user preferences storage and retrieval."""
    save_user_preference("user_123", "default_currency", "INR", db=test_db)
    save_user_preference("user_123", "notification_email", "user@company.com", db=test_db)

    prefs = get_user_preferences("user_123", db=test_db)
    assert prefs["default_currency"] == "INR"
    assert prefs["notification_email"] == "user@company.com"

    # Update preference
    save_user_preference("user_123", "default_currency", "USD", db=test_db)
    updated = get_user_preferences("user_123", db=test_db)
    assert updated["default_currency"] == "USD"


def test_memory_persistence_node_execution(test_db):
    """Test the memory persistence agent node correctly updates Blackboard state."""
    state = ExpenseReportState(
        user_id="demo_user",
        run_id="run-node-test-isolated",
        date_range=DateRange(start_date=date(2026, 6, 1), end_date=date(2026, 6, 30)),
        totals={"confirmed_total": 5200.0, "Lodging": 5200.0},
        provisional_totals={"provisional_total": 0.0},
        review_result=ReviewResult(overall_status="passed", findings=[]),
        delivery_status="pending"
    )

    state = persist_memory_node(state, db=test_db)
    assert state.agent_status["Memory Persistence"] == "COMPLETED"
    assert state.report_id is not None
    assert state.report_id.startswith("RPT-")
