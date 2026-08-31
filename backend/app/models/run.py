from sqlalchemy import Column, String, Integer, DateTime
from app.database import Base
from datetime import datetime

class RunModel(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    request_text = Column(String)
    status = Column(String, default="running")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class AgentLogModel(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    agent = Column(String)
    action = Column(String)
    status = Column(String)
    input_summary = Column(String, nullable=True)
    output_summary = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    errors = Column(String, nullable=True)
