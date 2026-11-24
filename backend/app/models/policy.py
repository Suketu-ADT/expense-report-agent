from sqlalchemy import Column, Integer, LargeBinary, String, Text
from app.database import Base


class PolicyRun(Base):
    __tablename__ = "policy_runs"
    run_id = Column(String, primary_key=True)
    snapshot = Column(Text, nullable=False)

class ReceiptDocument(Base):
    __tablename__ = "receipt_documents"
    run_id = Column(String, primary_key=True)
    item_index = Column(Integer, primary_key=True)
    media_type = Column(String, nullable=False)
    content = Column(LargeBinary, nullable=False)
