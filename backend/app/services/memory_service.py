"""
Memory service: tools for saving and retrieving persistent memory.
Implements Unit III long-term memory using SQLite via SQLAlchemy.
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.memory import ReportHistoryModel, AgentMessageModel, UserPreferenceModel


# ── Report History (Long-Term Memory) ──────────────────────────────────

def save_report_summary(
    run_id: str,
    user_id: str,
    period_start: str,
    period_end: str,
    period_label: str,
    confirmed_total: float,
    provisional_total: float,
    category_totals: Dict[str, float],
    total_expenses: int,
    flagged_count: int,
    excluded_count: int,
    review_status: str,
    review_findings: List[Dict[str, Any]],
    report_file_path: Optional[str] = None,
    delivery_status: str = "pending",
    db: Optional[Session] = None,
) -> str:
    """Save a completed report summary to persistent storage idempotently. Returns report_id."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        existing = None
        if run_id and run_id != "unknown":
            existing = db.query(ReportHistoryModel).filter(
                ReportHistoryModel.run_id == run_id
            ).first()

        if existing:
            existing.user_id = user_id
            existing.period_start = period_start
            existing.period_end = period_end
            existing.period_label = period_label
            existing.confirmed_total = confirmed_total
            existing.provisional_total = provisional_total
            existing.category_totals = json.dumps(category_totals)
            existing.total_expenses = total_expenses
            existing.flagged_count = flagged_count
            existing.excluded_count = excluded_count
            existing.review_status = review_status
            existing.review_findings = json.dumps(review_findings)
            existing.report_file_path = report_file_path
            existing.delivery_status = delivery_status
            existing.updated_at = datetime.utcnow()
            db.commit()
            return existing.report_id

        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
        record = ReportHistoryModel(
            report_id=report_id,
            run_id=run_id,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            period_label=period_label,
            confirmed_total=confirmed_total,
            provisional_total=provisional_total,
            category_totals=json.dumps(category_totals),
            total_expenses=total_expenses,
            flagged_count=flagged_count,
            excluded_count=excluded_count,
            review_status=review_status,
            review_findings=json.dumps(review_findings),
            report_file_path=report_file_path,
            delivery_status=delivery_status,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return report_id
    except Exception as e:
        db.rollback()
        raise e
    finally:
        if close_db:
            db.close()


def get_report_by_id(report_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a previously saved report by its report_id."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        record = db.query(ReportHistoryModel).filter(
            ReportHistoryModel.report_id == report_id
        ).first()
        if record is None:
            return None
        return _report_to_dict(record)
    finally:
        if close_db:
            db.close()


def get_reports_by_period(period_label: str, user_id: Optional[str] = None, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Retrieve reports matching a reporting period label."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        query = db.query(ReportHistoryModel).filter(
            ReportHistoryModel.period_label == period_label
        )
        if user_id:
            query = query.filter(ReportHistoryModel.user_id == user_id)
        records = query.order_by(ReportHistoryModel.created_at.desc()).all()
        return [_report_to_dict(r) for r in records]
    finally:
        if close_db:
            db.close()


def get_all_reports(user_id: Optional[str] = None, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Retrieve all report summaries, optionally filtered by user_id."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        query = db.query(ReportHistoryModel)
        if user_id:
            query = query.filter(ReportHistoryModel.user_id == user_id)
        records = query.order_by(ReportHistoryModel.created_at.desc()).all()
        return [_report_to_dict(r) for r in records]
    finally:
        if close_db:
            db.close()


def _report_to_dict(record: ReportHistoryModel) -> Dict[str, Any]:
    """Convert a ReportHistoryModel to a dictionary."""
    return {
        "report_id": record.report_id,
        "run_id": record.run_id,
        "user_id": record.user_id,
        "period_start": record.period_start,
        "period_end": record.period_end,
        "period_label": record.period_label,
        "confirmed_total": record.confirmed_total,
        "provisional_total": record.provisional_total,
        "category_totals": json.loads(record.category_totals) if record.category_totals else {},
        "total_expenses": record.total_expenses,
        "flagged_count": record.flagged_count,
        "excluded_count": record.excluded_count,
        "review_status": record.review_status,
        "review_findings": json.loads(record.review_findings) if record.review_findings else [],
        "report_file_path": record.report_file_path,
        "delivery_status": record.delivery_status,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


# ── Agent Messages ─────────────────────────────────────────────────────

def save_agent_message(
    run_id: str,
    sender: str,
    recipient: str,
    message_type: str,
    status: str = "sent",
    findings: Optional[List[Dict[str, Any]]] = None,
    requested_action: Optional[str] = None,
    task_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> int:
    """Save an inter-agent message for audit trail."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        record = AgentMessageModel(
            run_id=run_id,
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            task_id=task_id,
            status=status,
            findings=json.dumps(findings) if findings else None,
            requested_action=requested_action,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record.id
    except Exception as e:
        db.rollback()
        raise e
    finally:
        if close_db:
            db.close()


def get_agent_messages(run_id: str, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Retrieve all inter-agent messages for a given run."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        records = db.query(AgentMessageModel).filter(
            AgentMessageModel.run_id == run_id
        ).order_by(AgentMessageModel.timestamp.asc()).all()
        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "sender": r.sender,
                "recipient": r.recipient,
                "message_type": r.message_type,
                "task_id": r.task_id,
                "status": r.status,
                "findings": json.loads(r.findings) if r.findings else [],
                "requested_action": r.requested_action,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in records
        ]
    finally:
        if close_db:
            db.close()


# ── User Preferences ───────────────────────────────────────────────────

def save_user_preference(user_id: str, key: str, value: str, db: Optional[Session] = None) -> None:
    """Save or update a user preference."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        existing = db.query(UserPreferenceModel).filter(
            UserPreferenceModel.user_id == user_id,
            UserPreferenceModel.preference_key == key,
        ).first()
        if existing:
            existing.preference_value = value
            existing.updated_at = datetime.utcnow()
        else:
            record = UserPreferenceModel(
                user_id=user_id,
                preference_key=key,
                preference_value=value,
            )
            db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        if close_db:
            db.close()


def get_user_preferences(user_id: str, db: Optional[Session] = None) -> Dict[str, str]:
    """Retrieve all preferences for a user."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        records = db.query(UserPreferenceModel).filter(
            UserPreferenceModel.user_id == user_id
        ).all()
        return {r.preference_key: r.preference_value for r in records}
    finally:
        if close_db:
            db.close()
