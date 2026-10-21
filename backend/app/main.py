from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import threading
from typing import Optional

from app.database import engine, Base, get_db, SessionLocal
from app.models.run import RunModel, AgentLogModel
from app.models.memory import ReportHistoryModel, AgentMessageModel
from app.schemas.agent import RunRequest, RunResponse
from app.graph.expense_graph import expense_graph
from app.state.blackboard import ExpenseReportState
from app.services.memory_service import (
    get_all_reports, get_report_by_id, get_reports_by_period,
    get_agent_messages, get_user_preferences, save_user_preference
)
from dotenv import load_dotenv

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Expense Report Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active runs to serve live frontend updates
# Real-world apps might use Redis + WebSocket or similar
active_runs = {}

def execute_run(run_id: str, user_id: str, request_text: str, inject_discrepancy: bool = False):
    db = SessionLocal()
    try:
        initial_state = ExpenseReportState(
            user_id=user_id,
            request_text=request_text,
            run_id=run_id,
            inject_discrepancy=inject_discrepancy,
        )
        active_runs[run_id] = initial_state
        logged_count = 0
        
        # We process the graph synchronously within this background thread
        for event in expense_graph.stream(initial_state, stream_mode="values"):
            # With stream_mode="values", event is the full state dict or BaseModel
            if isinstance(event, dict):
                state = ExpenseReportState(**event)
            else:
                state = event
                
            active_runs[run_id] = state
                    
            # Store new logs in DB
            if hasattr(state, "run_log") and state.run_log:
                new_logs = state.run_log[logged_count:]
                for log_item in new_logs:
                    db_log = AgentLogModel(
                        run_id=run_id,
                        agent=log_item.get("agent"),
                        action=log_item.get("action"),
                        status=log_item.get("status"),
                        errors=log_item.get("error")
                    )
                    db.add(db_log)
                db.commit()
                logged_count = len(state.run_log)

        # Update run status in DB
        db_run = db.query(RunModel).filter(RunModel.id == run_id).first()
        if db_run:
            has_fatal_failure = bool(state.errors and state.agent_status.get("Report Generation") != "COMPLETED")
            db_run.status = "failed" if has_fatal_failure else "completed"
            db.commit()
    except Exception as e:
        print(f"Run failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            db_run = db.query(RunModel).filter(RunModel.id == run_id).first()
            if db_run:
                db_run.status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/run", response_model=RunResponse)
def start_run(request: RunRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    run_id = str(uuid.uuid4())
    
    db_run = RunModel(
        id=run_id,
        user_id=request.user_id,
        request_text=request.request_text,
        status="running"
    )
    db.add(db_run)
    db.commit()
    
    background_tasks.add_task(
        execute_run, run_id, request.user_id, request.request_text,
        inject_discrepancy=request.inject_discrepancy
    )
    
    return RunResponse(run_id=run_id, status="running", message="Agent pipeline started")

@app.get("/api/run/{run_id}")
def get_run_status(run_id: str, db: Session = Depends(get_db)):
    db_run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    state = active_runs.get(run_id)
    if not state:
        return {"status": db_run.status, "message": "State not found in memory"}
        
    # Build review result dict
    review_result_dict = None
    if state.review_result:
        review_result_dict = {
            "overall_status": state.review_result.overall_status,
            "findings": [f.model_dump() for f in state.review_result.findings],
            "reviewed_at": state.review_result.reviewed_at,
        }

    # Build agent messages list
    agent_messages_list = [m.model_dump() for m in state.agent_messages] if state.agent_messages else []

    return {
        "status": db_run.status,
        "current_agent": state.current_agent,
        "agent_status": state.agent_status,
        "totals": state.totals,
        "provisional_totals": state.provisional_totals,
        "raw_expenses": [e.model_dump() for e in state.raw_expenses],
        "filtered_expenses": [e.model_dump() for e in state.filtered_expenses],
        "missing_data_flags": [f.model_dump() for f in state.missing_data_flags],
        "categorized_expenses": [e.model_dump() for e in state.categorized_expenses],
        "errors": state.errors,
        "date_range": state.date_range.model_dump() if state.date_range else None,
        "delivery_status": state.delivery_status,
        # Unit III & IV additions
        "report_id": state.report_id,
        "historical_context": state.historical_context,
        "review_result": review_result_dict,
        "agent_messages": agent_messages_list,
        "retry_count": state.retry_count,
        "needs_human_review": state.needs_human_review,
        "approval_status": state.approval_status,
    }

@app.post("/api/run/{run_id}/approve")
def approve_run(run_id: str, db: Session = Depends(get_db)):
    """Human approval: approve a held report and dispatch the email."""
    state = active_runs.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found in memory")
    state.approval_status = "approved"
    state.needs_human_review = False

    # Execute email dispatch
    from app.agents.email_agent import email_node
    new_state = email_node(state)
    active_runs[run_id] = new_state

    # Update delivery status in persistent memory if report exists
    if new_state.report_id:
        try:
            report_rec = db.query(ReportHistoryModel).filter(
                ReportHistoryModel.report_id == new_state.report_id
            ).first()
            if report_rec:
                report_rec.delivery_status = new_state.delivery_status
                db.commit()
        except Exception:
            pass

    return {
        "status": "approved",
        "approval_status": "approved",
        "delivery_status": new_state.delivery_status,
        "message": "Report approved and email dispatched successfully"
    }

@app.post("/api/run/{run_id}/reject")
def reject_run(run_id: str, db: Session = Depends(get_db)):
    """Human approval: reject a report, halting email dispatch."""
    state = active_runs.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found in memory")
    state.approval_status = "rejected"
    return {
        "status": "rejected",
        "approval_status": "rejected",
        "delivery_status": state.delivery_status,
        "message": "Report rejected by reviewer. Dispatch cancelled."
    }

@app.get("/api/run/{run_id}/logs")
def get_run_logs(run_id: str, db: Session = Depends(get_db)):
    logs = db.query(AgentLogModel).filter(AgentLogModel.run_id == run_id).all()
    return [{"timestamp": f"{log.timestamp.isoformat()}Z" if log.timestamp else None, "agent": log.agent, "action": log.action, "status": log.status, "errors": log.errors} for log in logs]

@app.post("/api/expenses/import")
async def import_expenses(file: UploadFile = File(...)):
    import os
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, 'expenses.csv')
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        return {"status": "success", "message": "Expenses imported successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Unit III: Memory / Report History API ──────────────────────────────

@app.get("/api/reports/history")
def get_report_history(
    user_id: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Retrieve report history. Optionally filter by user_id or period label."""
    if period:
        reports = get_reports_by_period(period, user_id=user_id, db=db)
    else:
        reports = get_all_reports(user_id=user_id, db=db)
    return {"reports": reports, "count": len(reports)}

@app.get("/api/reports/{report_id}")
def get_saved_report(report_id: str, db: Session = Depends(get_db)):
    """Retrieve a specific saved report by report_id."""
    report = get_report_by_id(report_id, db=db)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@app.get("/api/run/{run_id}/messages")
def get_run_messages(run_id: str, db: Session = Depends(get_db)):
    """Retrieve inter-agent messages for a specific run."""
    messages = get_agent_messages(run_id, db=db)
    return {"messages": messages, "count": len(messages)}

@app.get("/api/preferences/{user_id}")
def get_preferences(user_id: str, db: Session = Depends(get_db)):
    """Retrieve user preferences."""
    prefs = get_user_preferences(user_id, db=db)
    return {"preferences": prefs}

@app.post("/api/preferences/{user_id}")
def set_preference(user_id: str, key: str, value: str, db: Session = Depends(get_db)):
    """Save or update a user preference."""
    save_user_preference(user_id, key, value, db=db)
    return {"status": "saved", "key": key, "value": value}
