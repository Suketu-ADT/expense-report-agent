import pytest
from fastapi.testclient import TestClient
from app.main import app, active_runs
from app.state.blackboard import ExpenseReportState, DateRange
from datetime import date


@pytest.fixture
def client():
    return TestClient(app)


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_report_history_empty_and_retrieval(client):
    # Retrieve history
    response = client.get("/api/reports/history")
    assert response.status_code == 200
    data = response.json()
    assert "reports" in data
    assert "count" in data


def test_api_saved_report_not_found(client):
    response = client.get("/api/reports/RPT-DOESNOTEXIST")
    assert response.status_code == 404


def test_api_user_preferences_flow(client):
    # Set preference
    res_set = client.post("/api/preferences/test_user_api?key=theme&value=dark")
    assert res_set.status_code == 200
    assert res_set.json()["status"] == "saved"

    # Get preferences
    res_get = client.get("/api/preferences/test_user_api")
    assert res_get.status_code == 200
    assert res_get.json()["preferences"].get("theme") == "dark"


def test_api_approve_and_reject_flow(client):
    run_id = "test-run-approval"
    # Seed active_runs with a state awaiting human review
    test_state = ExpenseReportState(
        user_id="test_user",
        run_id=run_id,
        date_range=DateRange(start_date=date(2026, 6, 1), end_date=date(2026, 6, 30)),
        totals={"confirmed_total": 100.0},
        provisional_totals={"provisional_total": 0.0},
        needs_human_review=True,
        approval_status="pending",
        delivery_status="pending",
    )
    active_runs[run_id] = test_state

    # Approve run
    res_approve = client.post(f"/api/run/{run_id}/approve")
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "approved"
    assert active_runs[run_id].approval_status == "approved"

    # Reject another run
    run_id_2 = "test-run-reject"
    active_runs[run_id_2] = ExpenseReportState(
        user_id="test_user",
        run_id=run_id_2,
        approval_status="pending",
    )
    res_reject = client.post(f"/api/run/{run_id_2}/reject")
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "rejected"
    assert active_runs[run_id_2].approval_status == "rejected"
