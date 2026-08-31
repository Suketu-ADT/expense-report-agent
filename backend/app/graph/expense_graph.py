from langgraph.graph import StateGraph, END
from app.state.blackboard import ExpenseReportState
from app.agents.orchestrator import orchestrator_node
from app.agents.retrieval_agent import retrieval_node
from app.agents.validation_agent import validation_node
from app.agents.categorization_agent import categorization_node
from app.agents.calculation_agent import calculation_node
from app.agents.report_agent import report_node
from app.agents.email_agent import email_node

def check_retrieval(state: ExpenseReportState) -> str:
    if state.agent_status.get("Data Retrieval") == "FAILED":
        return "end"
    if not state.raw_expenses:
        state.run_log.append({"agent": "System", "action": "Zero expenses", "status": "COMPLETED"})
        return "end"
    return "validation"

def check_validation(state: ExpenseReportState) -> str:
    if not state.filtered_expenses:
        return "end"
    return "categorization"

def check_report(state: ExpenseReportState) -> str:
    if state.agent_status.get("Report Generation") == "FAILED":
        return "end"
    return "email"

def build_graph():
    builder = StateGraph(ExpenseReportState)
    
    # Add nodes
    builder.add_node("Orchestrator", orchestrator_node)
    builder.add_node("Data Retrieval", retrieval_node)
    builder.add_node("Filter & Validation", validation_node)
    builder.add_node("Categorization", categorization_node)
    builder.add_node("Calculation", calculation_node)
    builder.add_node("Report Generation", report_node)
    builder.add_node("Email Dispatch", email_node)
    
    # Add edges
    builder.set_entry_point("Orchestrator")
    builder.add_edge("Orchestrator", "Data Retrieval")
    
    builder.add_conditional_edges(
        "Data Retrieval",
        check_retrieval,
        {"validation": "Filter & Validation", "end": END}
    )
    
    builder.add_conditional_edges(
        "Filter & Validation",
        check_validation,
        {"categorization": "Categorization", "end": END}
    )
    
    builder.add_edge("Categorization", "Calculation")
    builder.add_edge("Calculation", "Report Generation")
    
    builder.add_conditional_edges(
        "Report Generation",
        check_report,
        {"email": "Email Dispatch", "end": END}
    )
    
    builder.add_edge("Email Dispatch", END)
    
    return builder.compile()

expense_graph = build_graph()
