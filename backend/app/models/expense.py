from sqlalchemy import Column, String, Float, Boolean, Date, Integer
from app.database import Base

class ExpenseModel(Base):
    __tablename__ = "expenses"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    date = Column(Date, nullable=True)
    merchant = Column(String)
    amount = Column(Float, nullable=True)
    currency = Column(String)
    category_hint = Column(String, nullable=True)
    receipt_reference = Column(String, nullable=True)
