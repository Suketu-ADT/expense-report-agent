from pydantic import BaseModel
from typing import Optional

class RunRequest(BaseModel):
    request_text: str = "Generate my travel expense report for last month and email it to finance."
    user_id: str = "demo_user"

class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str
