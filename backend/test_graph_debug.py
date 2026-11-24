"""Quick diagnostic to find why pipeline stops after Filter & Validation."""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from app.state.blackboard import ExpenseReportState
from app.graph.expense_graph import expense_graph

initial_state = ExpenseReportState(
    user_id="test_user",
    request_text="Generate my business travel expense report for June 2026 from the uploaded CSV"
)

print("=== Running graph ===")
step = 0
try:
    for event in expense_graph.stream(initial_state, stream_mode="values"):
        step += 1
        if isinstance(event, dict):
            state = ExpenseReportState(**event)
        else:
            state = event
        
        print(f"\n--- Step {step} ---")
        print(f"  current_agent: {state.current_agent}")
        print(f"  agent_status: {state.agent_status}")
        print(f"  raw_expenses count: {len(state.raw_expenses)}")
        print(f"  filtered_expenses count: {len(state.filtered_expenses)}")
        print(f"  categorized_expenses count: {len(state.categorized_expenses)}")
        print(f"  totals: {state.totals}")
        print(f"  date_range: {state.date_range}")
        if state.errors:
            print(f"  ERRORS: {state.errors}")
except Exception as e:
    print(f"\n!!! EXCEPTION at step {step}: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Done ===")
