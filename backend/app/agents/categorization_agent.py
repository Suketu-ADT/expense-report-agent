from app.state.blackboard import ExpenseReportState, CategorizedExpense
from app.services.llm_service import categorize_with_reflection
from app.services.guardrails import contains_injection_attempt

def categorization_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Categorization"
    state.agent_status["Categorization"] = "RUNNING"
    
    categorized = []
    
    # Simple deterministic rules
    rules = {
        "Airfare": ["indigo", "air india", "emirates", "vistara", "airlines", "flight"],
        "Lodging": ["hotel", "taj", "marriott", "hyatt", "hilton"],
        "Meals": ["restaurant", "cafe", "starbucks", "zomato", "swiggy", "coffee", "dinner", "lunch", "food"],
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
            if contains_injection_attempt(exp.merchant) or contains_injection_attempt(exp.category_hint or ""):
                state.run_log.append({
                    "agent": "Categorization",
                    "action": f"Sanitized a suspicious merchant/hint field before calling the LLM for {exp.id}",
                    "status": "WARNING",
                })
            category_assigned, critique, revised = categorize_with_reflection(
                exp.merchant, exp.amount or 0.0, exp.category_hint or ""
            )
            if critique:
                action = f"Reflected on {exp.id} ({exp.merchant}): {critique}"
                if revised:
                    action += f" — revised to {category_assigned}"
                state.run_log.append({"agent": "Categorization", "action": action, "status": "COMPLETED"})

        categorized.append(CategorizedExpense(**exp.model_dump(), category=category_assigned))
        
    state.categorized_expenses = categorized
    state.agent_status["Categorization"] = "COMPLETED"
    state.run_log.append({
        "agent": "Categorization", 
        "action": "Categories assigned", 
        "status": "COMPLETED"
    })
    
    return state
