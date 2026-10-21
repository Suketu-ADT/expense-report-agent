from app.state.blackboard import ExpenseReportState, DataQualityFlag, DateRange
from datetime import date
import calendar

def validation_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Filter & Validation"
    state.agent_status["Filter & Validation"] = "RUNNING"
    
    start_date = state.date_range.start_date if state.date_range else date.min
    end_date = state.date_range.end_date if state.date_range else date.max
    
    # Check if raw_expenses exist and if any dated records match the requested range
    dated_records = [exp for exp in state.raw_expenses if exp.date]
    records_in_range = [exp for exp in dated_records if start_date <= exp.date <= end_date]

    # If the requested date range yielded 0 records, but raw records exist for a specific month,
    # align date_range to match the available records rather than discarding all valid data.
    if dated_records and not records_in_range:
        first_date = dated_records[0].date
        new_start = first_date.replace(day=1)
        new_end = first_date.replace(day=calendar.monthrange(first_date.year, first_date.month)[1])
        orig_label = state.date_range.start_date.strftime('%B %Y') if state.date_range else 'unspecified'
        state.date_range = DateRange(start_date=new_start, end_date=new_end)
        start_date = new_start
        end_date = new_end
        new_label = new_start.strftime('%B %Y')
        state.run_log.append({
            "agent": "Filter & Validation",
            "action": f"Adjusted reporting period from {orig_label} to {new_label} to match available expense records",
            "status": "COMPLETED"
        })

    valid_expenses = []
    seen_records = set() # For duplicate detection (date, merchant, amount)
    
    for exp in state.raw_expenses:
        # Date check
        if not exp.date:
            state.missing_data_flags.append(DataQualityFlag(
                expense_id=exp.id,
                problem="Missing date",
                action_required="Provide date for expense",
                status="NEEDS_REVIEW"
            ))
            # Preserve as flagged provisional item (requires review)
            valid_expenses.append(exp)
            continue
            
        # Filter by month
        if not (start_date <= exp.date <= end_date):
            continue
            
        # Amount check
        if exp.amount is None:
            state.missing_data_flags.append(DataQualityFlag(
                expense_id=exp.id,
                problem="Missing amount",
                action_required="Provide amount for expense",
                status="NEEDS_REVIEW"
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
                action_required="Resolve currency conversion",
                status="NEEDS_REVIEW"
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

