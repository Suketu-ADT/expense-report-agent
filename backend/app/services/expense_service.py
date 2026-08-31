import csv
from typing import List, Dict, Any
from app.state.blackboard import Expense
from datetime import datetime
import os

def get_expenses(user_id: str) -> List[Expense]:
    expenses = []
    csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'expenses.csv')
    
    if not os.path.exists(csv_path):
        return expenses

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            date_val = None
            if row.get('date') and row['date'].lower() != 'missing':
                try:
                    date_val = datetime.strptime(row['date'], '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            amount_val = None
            if row.get('amount') and row['amount'].lower() != 'missing':
                try:
                    amount_val = float(row['amount'])
                except ValueError:
                    pass
            
            expenses.append(Expense(
                id=f"exp_{i}",
                date=date_val,
                merchant=row.get('merchant', ''),
                amount=amount_val,
                currency=row.get('currency', ''),
                category_hint=row.get('category_hint', ''),
                receipt_reference=row.get('receipt_reference', '')
            ))
    
    return expenses
