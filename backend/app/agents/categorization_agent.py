from app.state.blackboard import ExpenseReportState, CategorizedExpense
from app.services.llm_service import categorize_expense_with_llm

def categorization_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Categorization"
    state.agent_status["Categorization"] = "RUNNING"
    
    categorized = []
    
    # Simple deterministic rules
    rules = {
        "Airfare": ["indigo", "air india", "emirates", "vistara", "airlines", "flight"],
        "Lodging": ["hotel", "taj", "marriott", "hyatt", "hilton"],
        "Meals": ["restaurant", "cafe", "starbucks", "zomato", "swiggy", "coffee"],
        "Ground Transport": ["uber", "ola", "taxi", "metro", "bus"]
    }
    
    for exp in state.filtered_expenses:
        merchant_lower = exp.merchant.lower()
        category_assigned = None
        
        for cat, keywords in rules.items():
            if any(kw in merchant_lower for kw in keywords):
                category_assigned = cat
                break
                
        if not category_assigned:
            category_assigned = categorize_expense_with_llm(exp.merchant, exp.amount or 0.0, exp.category_hint or "")
            
        categorized.append(CategorizedExpense(**exp.model_dump(), category=category_assigned))
        
    state.categorized_expenses = categorized
    state.agent_status["Categorization"] = "COMPLETED"
    state.run_log.append({
        "agent": "Categorization", 
        "action": "Categories assigned", 
        "status": "COMPLETED"
    })
    
    return state
