from pydantic import BaseModel
from typing import Optional

from app.services.reimbursement import PolicyOptions

class RunRequest(BaseModel):
    policy: Optional[PolicyOptions] = None
    request_text: str = "Generate my travel expense report for last month and email it to finance."
    user_id: str = "demo_user"
    inject_discrepancy: bool = False  # Dev-only: inject a controlled test discrepancy
    autonomy_level: str = "co_pilot"  # "cautious" | "co_pilot" | "trusting"

class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str
