from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import threading

from app.database import engine, Base, get_db
from app.models.run import RunModel, AgentLogModel
from app.schemas.agent import RunRequest, RunResponse
from app.graph.expense_graph import expense_graph
from app.state.blackboard import ExpenseReportState
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

def execute_run(run_id: str, user_id: str, request_text: str, db: Session):
    try:
        initial_state = ExpenseReportState(user_id=user_id)
        active_runs[run_id] = initial_state
        
        # We process the graph synchronously within this background thread
        for event in expense_graph.stream(initial_state, stream_mode="values"):
            # With stream_mode="values", event is the full state dict or BaseModel
            if isinstance(event, dict):
                state = ExpenseReportState(**event)
            else:
                state = event
                
            active_runs[run_id] = state
                    
            # Store logs in DB
            if hasattr(state, "run_log") and state.run_log:
                # To avoid duplicate inserts, we just check the latest log
                latest_log = state.run_log[-1]
                db_log = AgentLogModel(
                    run_id=run_id,
                    agent=latest_log.get("agent"),
                    action=latest_log.get("action"),
                    status=latest_log.get("status"),
                    errors=latest_log.get("error")
                )
                db.add(db_log)
                db.commit()

        # Update run status in DB
        db_run = db.query(RunModel).filter(RunModel.id == run_id).first()
        if db_run:
            db_run.status = "completed"
            db.commit()
    except Exception as e:
        print(f"Run failed: {e}")
        db_run = db.query(RunModel).filter(RunModel.id == run_id).first()
        if db_run:
            db_run.status = "failed"
            db.commit()

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
    
    background_tasks.add_task(execute_run, run_id, request.user_id, request.request_text, db)
    
    return RunResponse(run_id=run_id, status="running", message="Agent pipeline started")

@app.get("/api/run/{run_id}")
def get_run_status(run_id: str, db: Session = Depends(get_db)):
    db_run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    state = active_runs.get(run_id)
    if not state:
        return {"status": db_run.status, "message": "State not found in memory"}
        
    return {
        "status": db_run.status,
        "current_agent": state.current_agent,
        "agent_status": state.agent_status,
        "totals": state.totals,
        "provisional_totals": state.provisional_totals,
        "filtered_expenses": [e.model_dump() for e in state.filtered_expenses],
        "missing_data_flags": [f.model_dump() for f in state.missing_data_flags],
        "categorized_expenses": [e.model_dump() for e in state.categorized_expenses],
        "errors": state.errors
    }

@app.get("/api/run/{run_id}/logs")
def get_run_logs(run_id: str, db: Session = Depends(get_db)):
    logs = db.query(AgentLogModel).filter(AgentLogModel.run_id == run_id).all()
    return [{"timestamp": log.timestamp, "agent": log.agent, "action": log.action, "status": log.status, "errors": log.errors} for log in logs]

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

