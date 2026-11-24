from app.state.blackboard import ExpenseReportState
from app.services.expense_service import get_expenses

def retrieval_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Data Retrieval"
    state.agent_status["Data Retrieval"] = "RUNNING"
    
    try:
        from app.services.reimbursement import jury_claims
        raw_data = (jury_claims(state.resolution_demo) if state.policy_demo or state.resolution_demo
                    else get_expenses(state.user_id))
        state.raw_expenses = raw_data
        state.agent_status["Data Retrieval"] = "COMPLETED"
        state.run_log.append({
            "agent": "Data Retrieval", 
            "action": f"Loaded {len(raw_data)} raw records", 
            "status": "COMPLETED"
        })
    except Exception as e:
        state.agent_status["Data Retrieval"] = "FAILED"
        state.errors.append(str(e))
        state.run_log.append({
            "agent": "Data Retrieval", 
            "action": "Load records", 
            "status": "FAILED",
            "error": str(e)
        })
        
    return state
