from app.state.blackboard import ExpenseReportState
from decimal import Decimal

def calculation_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Calculation"
    state.agent_status["Calculation"] = "RUNNING"
    
    confirmed_total = Decimal('0.00')
    provisional_total = Decimal('0.00')
    subtotals = {}
    
    flagged_ids = {f.expense_id for f in state.missing_data_flags if f.status == "NEEDS_REVIEW"}
    
    for exp in state.categorized_expenses:
        amount = Decimal(str(exp.amount)) if exp.amount is not None else Decimal('0.00')
        
        if exp.id in flagged_ids:
            provisional_total += amount
        else:
            confirmed_total += amount
            subtotals[exp.category] = subtotals.get(exp.category, Decimal('0.00')) + amount
            
    state.totals["confirmed_total"] = float(confirmed_total)
    for k, v in subtotals.items():
        state.totals[k] = float(v)
        
    state.provisional_totals["provisional_total"] = float(provisional_total)
    
    state.agent_status["Calculation"] = "COMPLETED"
    state.run_log.append({
        "agent": "Calculation", 
        "action": f"Confirmed total: ₹{confirmed_total}", 
        "status": "COMPLETED"
    })
    
    return state
