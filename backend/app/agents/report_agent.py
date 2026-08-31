from app.state.blackboard import ExpenseReportState
from app.services.pdf_service import generate_pdf_report

def report_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Report Generation"
    state.agent_status["Report Generation"] = "RUNNING"
    
    try:
        report_path = generate_pdf_report(state, run_id=state.user_id) # Using user_id for simplicity or pass real run_id
        state.report_file = report_path
        
        state.agent_status["Report Generation"] = "COMPLETED"
        state.run_log.append({
            "agent": "Report Generation", 
            "action": "PDF generated", 
            "status": "COMPLETED"
        })
    except Exception as e:
        state.agent_status["Report Generation"] = "FAILED"
        state.errors.append(f"PDF generation failed: {e}")
        state.run_log.append({
            "agent": "Report Generation", 
            "action": "Generate PDF", 
            "status": "FAILED",
            "error": str(e)
        })
        
    return state
