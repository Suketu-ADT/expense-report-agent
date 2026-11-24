from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import threading
import time
from typing import Optional

from app.database import engine, Base, get_db, SessionLocal
from app.models.run import RunModel, AgentLogModel
from app.models.memory import ReportHistoryModel, AgentMessageModel
from app.schemas.agent import RunRequest, RunResponse
from app.graph.expense_graph import expense_graph
from app.state.blackboard import ExpenseReportState
from app.services.memory_service import (
    get_all_reports, get_report_by_id, get_reports_by_period,
    get_agent_messages, get_user_preferences, save_user_preference, refresh_cached_report
)
from app.models.policy import PolicyRun, ReceiptDocument
from app.agents.evidence_review_agent import receipt_in_use
from app.agents.exception_resolution_agent import resolve_receipts
from app.services.reimbursement import JURY_DATA, ItemEdit, edit_item, summary
from app.services.receipt_upload import MAX_BATCH_BYTES, MAX_BATCH_FILES, MAX_RECEIPT_BYTES, read_upload
from fastapi.responses import FileResponse, Response
from sqlalchemy import text
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

def execute_run(run_id: str, user_id: str, request_text: str, inject_discrepancy: bool = False, policy=None,
                 autonomy_level: str = "co_pilot"):
    db = SessionLocal()
    try:
        initial_state = ExpenseReportState(
            user_id=user_id,
            request_text=request_text,
            run_id=run_id,
            policy_demo=bool(policy and policy.demo),
            resolution_demo=bool(policy and policy.resolution_demo),
            meal_cap=policy.meal_cap if policy else None,
            inject_discrepancy=inject_discrepancy,
            autonomy_level=autonomy_level,
        )
        active_runs[run_id] = initial_state
        logged_count = 0

        # Observability: each stream event fires once a node has finished,
        # so the gap since the previous event is that just-finished node's
        # wall-clock latency. This needs no change to any individual agent.
        trace = []
        last_tick = time.perf_counter()
        last_agent = None

        # We process the graph synchronously within this background thread
        for event in expense_graph.stream(initial_state, stream_mode="values"):
            # With stream_mode="values", event is the full state dict or BaseModel
            if isinstance(event, dict):
                state = ExpenseReportState(**event)
            else:
                state = event

            now = time.perf_counter()
            if last_agent is not None:
                trace.append({"agent": last_agent, "duration_ms": round((now - last_tick) * 1000, 1)})
            last_agent, last_tick = state.current_agent, now

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

        # Attribute the final gap (last node to stream end) and attach the
        # completed trace to the state the dashboard/API will read.
        trace.append({"agent": last_agent, "duration_ms": round((time.perf_counter() - last_tick) * 1000, 1)})
        state.trace = trace
        active_runs[run_id] = state

        # Update run status in DB
        db_run = db.query(RunModel).filter(RunModel.id == run_id).first()
        if db_run:
            has_fatal_failure = bool(state.errors and state.agent_status.get("Report Generation") != "COMPLETED")
            if state.reimbursement:
                db.add(PolicyRun(run_id=run_id, snapshot=state.model_dump_json()))
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
        inject_discrepancy=request.inject_discrepancy, policy=request.policy,
        autonomy_level=request.autonomy_level,
    )
    
    return RunResponse(run_id=run_id, status="running", message="Agent pipeline started")

@app.get("/api/run/{run_id}")
def get_run_status(run_id: str, db: Session = Depends(get_db)):
    db_run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    saved = db.get(PolicyRun, run_id)
    state = ExpenseReportState.model_validate_json(saved.snapshot) if saved else active_runs.get(run_id)
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
        "run_id": run_id,
        "reimbursement": policy_view(state),
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
        # Unit II: Planning & Reasoning
        "intent": state.intent.model_dump() if state.intent else None,
        "comparison": state.comparison,
        "execution_plan": state.execution_plan,
        "autonomy_level": state.autonomy_level,
        "max_retries": state.max_retries,
        # Unit III: Tool use — currency conversion
        "currency_conversions": state.currency_conversions,
        "converted_total_inr": state.converted_total_inr,
        # Observability
        "trace": state.trace,
    }

def policy_view(state):
    if state.reimbursement is None:
        return None
    return {**state.reimbursement, **summary(state.reimbursement)}


def editable_run(run_id, db):
    # Serialize decisions and dispatch across API workers.
    db.execute(text("BEGIN IMMEDIATE"))
    saved = db.get(PolicyRun, run_id)
    state = ExpenseReportState.model_validate_json(saved.snapshot) if saved else active_runs.get(run_id)
    if not state:
        raise HTTPException(404, "Run not found")
    if state.meal_cap is not None:
        if not saved:
            raise HTTPException(409, "Wait for the policy run to finish")
        if state.approval_status == "rejected" or state.delivery_status == "delivered":
            raise HTTPException(409, "This report is closed")
    return state, saved


@app.post("/api/run/{run_id}/claims/{index}")
def update_claim(run_id: str, index: int, edit: ItemEdit, db: Session = Depends(get_db)):
    return save_claim(run_id, index, edit, db)


def editable_policy(run_id, revision, db):
    state, saved = editable_run(run_id, db)
    if not saved:
        raise HTTPException(404, "No policy review for this run")
    if revision != state.reimbursement["revision"]:
        raise HTTPException(409, "Review changed. Refresh before editing.")
    return state, saved


def save_claim(run_id, index, edit, db, document=None):
    state, saved = editable_policy(run_id, edit.revision, db)
    items = state.reimbursement["items"]
    if 0 <= index < len(items) and edit.action in {"attach", "correct", "accept"}:
        item = items[index]
        source = edit.text
        if edit.action == "accept":
            source = next((event["text"] for event in reversed(item["events"]) if event.get("text")), item["source"])
        if source.strip() and receipt_in_use(items, index, source):
            raise HTTPException(422, "Receipt already supports another claim in this report.")
    try:
        edit_item(state.reimbursement, index, edit)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if document:
        save_receipt_document(db, state, index, document)
    return persist_policy_review(db, state, saved)


def save_receipt_document(db, state, index, upload):
    db.add(ReceiptDocument(run_id=state.run_id, item_index=index,
                           media_type=upload.media_type, content=upload.content))
    state.reimbursement["items"][index]["document"] = True


def persist_policy_review(db, state, saved):
    from app.services.pdf_service import generate_pdf_report
    state.report_file = generate_pdf_report(state, f"{state.run_id}_{state.reimbursement['revision']}")
    history = db.query(ReportHistoryModel).filter_by(report_id=state.report_id).first()
    if history:
        history.report_file_path = state.report_file
        refresh_cached_report(history)
    saved.snapshot = state.model_dump_json()
    db.commit()
    return policy_view(state)


@app.get("/api/run/{run_id}/reimbursement.pdf")
def policy_pdf(run_id: str, db: Session = Depends(get_db)):
    saved = db.get(PolicyRun, run_id)
    if not saved:
        raise HTTPException(404, "Policy report unavailable")
    state = ExpenseReportState.model_validate_json(saved.snapshot)
    return FileResponse(state.report_file, media_type="application/pdf", filename="Reimbursement.pdf")


@app.post("/api/run/{run_id}/approve")
def approve_run(run_id: str, db: Session = Depends(get_db)):
    """Human approval: approve a held report and dispatch the email."""
    state, saved = editable_run(run_id, db)
    if saved and summary(state.reimbursement)["held"]:
        raise HTTPException(409, "Resolve every held claim before dispatch")
    state.approval_status = "approved"
    state.needs_human_review = False

    # Execute email dispatch
    from app.agents.email_agent import email_node
    new_state = email_node(state)
    active_runs[run_id] = new_state

    if saved:
        saved.snapshot = new_state.model_dump_json()
    # Update delivery status in persistent memory if report exists
    if new_state.report_id:
        report_rec = db.query(ReportHistoryModel).filter_by(report_id=new_state.report_id).first()
        if report_rec:
            report_rec.delivery_status = new_state.delivery_status
            refresh_cached_report(report_rec)

    db.commit()
    if new_state.delivery_status == "failed":
        raise HTTPException(502, "Email dispatch failed. Retry approval.")
    return {
        "status": "approved",
        "approval_status": "approved",
        "delivery_status": new_state.delivery_status,
        "message": "Report approved and email dispatched successfully"
    }

@app.post("/api/run/{run_id}/reject")
def reject_run(run_id: str, db: Session = Depends(get_db)):
    """Human approval: reject a report, halting email dispatch."""
    state, saved = editable_run(run_id, db)
    state.approval_status = "rejected"
    if saved:
        saved.snapshot = state.model_dump_json()
        db.commit()
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
    saved = db.get(PolicyRun, report["run_id"])
    if saved:
        report["reimbursement"] = policy_view(ExpenseReportState.model_validate_json(saved.snapshot))
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

@app.post("/api/run/{run_id}/claims/{index}/receipt")
def attach_receipt(run_id: str, index: int, revision: int = Query(ge=0), file: UploadFile = File(...),
                   db: Session = Depends(get_db)):
    content = file.file.read(MAX_RECEIPT_BYTES + 1)
    if len(content) > MAX_RECEIPT_BYTES:
        raise HTTPException(413, "Receipt exceeds 5 MB")
    try:
        upload = read_upload(file.filename or "Receipt", content)
        edit = ItemEdit(revision=revision, action="attach", text=upload.source)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return save_claim(run_id, index, edit, db, upload)


@app.post("/api/run/{run_id}/receipt-review")
def review_receipt_batch(run_id: str, revision: int = Query(ge=0), demo: bool = False,
                         files: list[UploadFile] | None = File(None), db: Session = Depends(get_db)):
    if demo and files:
        raise HTTPException(422, "Choose uploaded receipts or the demo batch.")
    if not demo and not files:
        raise HTTPException(422, "Select at least one receipt.")
    if files and len(files) > MAX_BATCH_FILES:
        raise HTTPException(422, f"Select up to {MAX_BATCH_FILES} receipts per batch.")
    if files and sum(file.size or 0 for file in files) > MAX_BATCH_BYTES:
        raise HTTPException(413, "The receipt batch exceeds 100 MB.")

    uploads, file_results = [], []
    for file in files or []:
        name = file.filename or "Unnamed receipt"
        content = file.file.read(MAX_RECEIPT_BYTES + 1)
        try:
            if len(content) > MAX_RECEIPT_BYTES:
                raise ValueError("Receipt exceeds 5 MB.")
            uploads.append(read_upload(name, content, retry_ocr=True))
        except ValueError as exc:
            file_results.append({"name": name[:160], "message": str(exc)})

    state, saved = editable_policy(run_id, revision, db)
    sheet = state.reimbursement
    if demo:
        if not sheet.get("resolution_demo"):
            raise HTTPException(422, "Start the receipt agent demo to use its sample receipt.")
        sample = JURY_DATA / "central-metro-receipt.txt"
        uploads.append(read_upload(sample.name, sample.read_bytes()))
    try:
        attachments = resolve_receipts(sheet, uploads, file_results)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    for index, upload in attachments.items():
        save_receipt_document(db, state, index, upload)
    return persist_policy_review(db, state, saved)


@app.get("/api/run/{run_id}/claims/{index}/receipt")
def original_receipt(run_id: str, index: int, db: Session = Depends(get_db)):
    doc = db.get(ReceiptDocument, (run_id, index))
    if not doc:
        raise HTTPException(404, "Receipt file unavailable")
    extension = {"application/pdf": "pdf", "text/plain": "txt", "image/png": "png", "image/jpeg": "jpg"}[doc.media_type]
    return Response(doc.content, media_type=doc.media_type, headers={
        "Content-Disposition": f'attachment; filename="receipt-{index + 1}.{extension}"',
        "X-Content-Type-Options": "nosniff",
    })
