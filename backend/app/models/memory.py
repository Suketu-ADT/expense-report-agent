from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON
from app.database import Base
from datetime import datetime


class ReportHistoryModel(Base):
    """Long-term persistent memory: stores completed report summaries across executions."""
    __tablename__ = "report_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(String, unique=True, index=True)
    run_id = Column(String, index=True)
    user_id = Column(String, index=True)
    period_start = Column(String)
    period_end = Column(String)
    period_label = Column(String)
    confirmed_total = Column(Float, default=0.0)
    provisional_total = Column(Float, default=0.0)
    category_totals = Column(Text, default="{}")  # JSON string
    total_expenses = Column(Integer, default=0)
    flagged_count = Column(Integer, default=0)
    excluded_count = Column(Integer, default=0)
    review_status = Column(String, default="pending")  # passed, needs_correction, needs_human_review
    review_findings = Column(Text, default="[]")  # JSON string
    report_file_path = Column(String, nullable=True)
    delivery_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentMessageModel(Base):
    """Persists structured inter-agent messages for audit trail."""
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(String, index=True)
    sender = Column(String)
    recipient = Column(String)
    message_type = Column(String)  # finding, correction_request, correction_result, info
    task_id = Column(String, nullable=True)
    status = Column(String, default="sent")
    findings = Column(Text, nullable=True)  # JSON string
    requested_action = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class UserPreferenceModel(Base):
    """Stores user-approved preferences across sessions."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, index=True)
    preference_key = Column(String)
    preference_value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
