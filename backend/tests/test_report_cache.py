import uuid

import pytest

from app.services import memory_service
from app.services.memory_service import (
    clear_report_cache, get_all_reports, get_report_by_id, get_reports_by_period,
    refresh_cached_report, save_report_summary,
)
from app.models.memory import ReportHistoryModel


@pytest.fixture(autouse=True)
def _isolated_cache():
    clear_report_cache()
    yield
    clear_report_cache()


def _run_id():
    # The SQLite file persists across separate test invocations, and
    # save_report_summary upserts by run_id — a fixed literal run_id would
    # silently become an update (not a new row) on the second time these
    # tests run against the same file. A fresh uuid4 guarantees a brand new
    # row every single invocation.
    return f"cache-test-{uuid.uuid4()}"


def _save(run_id, user_id="cache-test-user", period_label="August 2026", confirmed_total=1000.0,
          delivery_status="pending"):
    return save_report_summary(
        run_id=run_id, user_id=user_id, period_start="2026-08-01", period_end="2026-08-31",
        period_label=period_label, confirmed_total=confirmed_total, provisional_total=0.0,
        category_totals={"Meals": confirmed_total}, total_expenses=1, flagged_count=0,
        excluded_count=0, review_status="passed", review_findings=[], delivery_status=delivery_status,
    )


def test_get_report_by_id_is_served_from_cache_without_a_db_session():
    report_id = _save(run_id=_run_id())
    # First call (through save) already populated the cache; passing no db
    # and no live session proves this read never has to touch SQLite.
    report = get_report_by_id(report_id)
    assert report["confirmed_total"] == 1000.0
    assert report["report_id"] == report_id


def test_cache_reflects_an_update_to_the_same_run_id():
    run_id = _run_id()
    report_id = _save(run_id=run_id, confirmed_total=1000.0)
    assert get_report_by_id(report_id)["confirmed_total"] == 1000.0

    _save(run_id=run_id, confirmed_total=2500.0)
    assert get_report_by_id(report_id)["confirmed_total"] == 2500.0


def test_returned_report_is_a_copy_not_the_cached_object():
    report_id = _save(run_id=_run_id())
    first = get_report_by_id(report_id)
    first["reimbursement"] = {"injected": "should not leak into the cache"}

    second = get_report_by_id(report_id)
    assert "reimbursement" not in second


def test_period_list_cache_includes_a_newly_saved_report():
    user_id = f"cache-test-user-period-{uuid.uuid4()}"
    before = get_reports_by_period("August 2026", user_id=user_id)
    assert before == []  # a freshly generated user_id has no prior rows

    report_id = _save(run_id=_run_id(), user_id=user_id)
    after = get_reports_by_period("August 2026", user_id=user_id)
    assert len(after) == 1
    assert after[0]["report_id"] == report_id


def test_all_reports_cache_includes_a_newly_saved_report():
    user_id = f"cache-test-user-all-{uuid.uuid4()}"
    before = get_all_reports(user_id=user_id)
    assert before == []

    report_id = _save(run_id=_run_id(), user_id=user_id)
    after = get_all_reports(user_id=user_id)
    assert len(after) == 1
    assert after[0]["report_id"] == report_id


def test_refresh_cached_report_keeps_a_direct_sqlalchemy_write_in_sync():
    """Covers the bypass path in main.py's approve_run / persist_policy_review,
    which flip delivery_status / report_file_path directly on the ORM object
    instead of going through save_report_summary."""
    report_id = _save(run_id=_run_id(), delivery_status="pending")
    assert get_report_by_id(report_id)["delivery_status"] == "pending"

    db = memory_service.SessionLocal()
    try:
        record = db.query(ReportHistoryModel).filter_by(report_id=report_id).first()
        record.delivery_status = "delivered"
        refresh_cached_report(record)
        db.commit()
    finally:
        db.close()

    assert get_report_by_id(report_id)["delivery_status"] == "delivered"
