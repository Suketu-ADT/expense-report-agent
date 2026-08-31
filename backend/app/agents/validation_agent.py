from app.state.blackboard import ExpenseReportState, DataQualityFlag
from datetime import date

def validation_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Filter & Validation"
    state.agent_status["Filter & Validation"] = "RUNNING"
    
    start_date = state.date_range.start_date if state.date_range else date.min
    end_date = state.date_range.end_date if state.date_range else date.max
    
    valid_expenses = []
    seen_records = set() # For duplicate detection (date, merchant, amount)
    
    for exp in state.raw_expenses:
        # Date check
        if not exp.date:
            state.missing_data_flags.append(DataQualityFlag(
                expense_id=exp.id,
                problem="Missing date",
                action_required="Provide date for expense"
            ))
            continue
            
        # Filter by month
        if not (start_date <= exp.date <= end_date):
            continue
            
        # Amount check
        if exp.amount is None:
            state.missing_data_flags.append(DataQualityFlag(
                expense_id=exp.id,
                problem="Missing amount",
                action_required="Provide amount for expense"
            ))
            # Include it, but flagged (will be excluded from confirmed totals)
            valid_expenses.append(exp)
            continue
            
        # Duplicate detection
        sig = (exp.date, exp.merchant, exp.amount)
        if sig in seen_records:
            state.missing_data_flags.append(DataQualityFlag(
                expense_id=exp.id,
                problem="Duplicate",
                action_required="Verify duplicate",
                status="EXCLUDED"
            ))
            continue
        seen_records.add(sig)
        
        # Unsupported currency
        if exp.currency.upper() not in ["INR", "USD", "EUR", "GBP"]:
            state.missing_data_flags.append(DataQualityFlag(
                expense_id=exp.id,
                problem="Unsupported Currency",
                action_required="Resolve currency conversion"
            ))
            valid_expenses.append(exp)
            continue
            
        valid_expenses.append(exp)
        
    state.filtered_expenses = valid_expenses
    
    flag_count = len([f for f in state.missing_data_flags if f.status == "NEEDS_REVIEW"])
    state.agent_status["Filter & Validation"] = "COMPLETED"
    state.run_log.append({
        "agent": "Filter & Validation", 
        "action": f"{len(valid_expenses)} valid records, {flag_count} flagged", 
        "status": "COMPLETED"
    })
    
    return state
