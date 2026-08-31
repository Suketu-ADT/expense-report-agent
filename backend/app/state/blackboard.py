from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import date as dt_date

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

class ExpenseReportState(BaseModel):
    user_id: str
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
