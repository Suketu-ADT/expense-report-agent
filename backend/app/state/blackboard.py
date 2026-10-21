from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import date as dt_date, datetime


class DateRange(BaseModel):
    start_date: dt_date
    end_date: dt_date


class DataQualityFlag(BaseModel):
    expense_id: str
    problem: str
    action_required: str
    status: str = "NEEDS_REVIEW" # e.g. "NEEDS_REVIEW", "EXCLUDED", "RESOLVED"


class Expense(BaseModel):
    id: str
    date: Optional[dt_date] = None
    merchant: str
    amount: Optional[float] = None
    currency: str
    category_hint: Optional[str] = None
    receipt_reference: Optional[str] = None
    receipt_pending: bool = False


class CategorizedExpense(Expense):
    category: str


# ── Unit IV: Structured Agent Communication ────────────────────────────

class AgentMessage(BaseModel):
    """Structured message for inter-agent communication."""
    sender: str
    recipient: str
    message_type: str  # "finding", "correction_request", "correction_result", "info"
    task_id: Optional[str] = None
    status: str = "sent"
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    requested_action: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ReviewFinding(BaseModel):
    """A single finding from the Expense Review Agent."""
    finding_type: str  # "total_mismatch", "duplicate_included", "missing_field_unflagged", "category_mismatch", "report_inconsistency"
    severity: str  # "critical", "warning", "info"
    description: str
    affected_expense_ids: List[str] = Field(default_factory=list)
    responsible_agent: str  # e.g. "Calculation", "Filter & Validation"
    requested_correction: Optional[str] = None
    resolution_status: str = "unresolved"  # "unresolved", "resolved", "escalated"


class ReviewResult(BaseModel):
    """Structured result returned by the Expense Review Agent."""
    overall_status: str = "pending"  # "passed", "needs_correction", "needs_human_review"
    findings: List[ReviewFinding] = Field(default_factory=list)
    reviewed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExpenseReportState(BaseModel):
    user_id: str
    request_text: str = ""
    date_range: Optional[DateRange] = None

    raw_expenses: List[Expense] = Field(default_factory=list)
    filtered_expenses: List[Expense] = Field(default_factory=list)

    missing_data_flags: List[DataQualityFlag] = Field(default_factory=list)

    categorized_expenses: List[CategorizedExpense] = Field(default_factory=list)

    totals: Dict[str, float] = Field(default_factory=dict)
    provisional_totals: Dict[str, float] = Field(default_factory=dict)

    report_file: Optional[str] = None
    delivery_status: str = "pending"

    execution_plan: List[str] = Field(default_factory=list)
    current_agent: Optional[str] = None
    agent_status: Dict[str, str] = Field(default_factory=dict)
    run_log: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    # ── Unit III: Short-term working memory ────────────────────────────
    run_id: Optional[str] = None  # Track run_id for memory persistence
    report_id: Optional[str] = None  # ID of saved report in persistent memory
    historical_context: Optional[Dict[str, Any]] = None  # Retrieved past reports

    # ── Unit IV: Multi-agent collaboration ─────────────────────────────
    agent_messages: List[AgentMessage] = Field(default_factory=list)
    review_result: Optional[ReviewResult] = None
    retry_count: int = 0
    max_retries: int = 3
    approval_status: str = "pending"  # "pending", "approved", "rejected"
    needs_human_review: bool = False

    # ── Test injection support (dev-only) ──────────────────────────────
    inject_discrepancy: bool = False
