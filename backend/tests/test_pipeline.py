import pytest
from datetime import date
import os
from decimal import Decimal

from app.state.blackboard import ExpenseReportState, Expense, DateRange
from app.agents.orchestrator import resolve_last_month
from app.agents.validation_agent import validation_node
from app.agents.categorization_agent import categorization_node
from app.agents.calculation_agent import calculation_node

def test_resolve_last_month():
    # If today is Aug 31 2026, last month is July 1 - July 31
    current = date(2026, 8, 31)
    dr = resolve_last_month(current)
    assert dr.start_date == date(2026, 7, 1)
    assert dr.end_date == date(2026, 7, 31)

def test_validation_logic():
    state = ExpenseReportState(user_id="test", date_range=DateRange(start_date=date(2026, 7, 1), end_date=date(2026, 7, 31)))
    state.raw_expenses = [
        Expense(id="1", date=date(2026, 7, 5), merchant="IndiGo", amount=100.0, currency="INR"), # Valid
        Expense(id="2", date=None, merchant="Cafe", amount=50.0, currency="INR"), # Missing date
        Expense(id="3", date=date(2026, 7, 5), merchant="Uber", amount=None, currency="INR"), # Missing amount
        Expense(id="4", date=date(2026, 7, 5), merchant="IndiGo", amount=100.0, currency="INR"), # Duplicate of 1
        Expense(id="5", date=date(2026, 7, 6), merchant="Test", amount=10.0, currency="JPY"), # Unsupported currency
        Expense(id="6", date=date(2026, 6, 15), merchant="Old", amount=20.0, currency="INR") # Out of date range
    ]
    
    state = validation_node(state)
    
    # 1 is valid, 3 is valid (but flagged), 5 is valid (but flagged)
    # 2 is dropped from filtered (missing date entirely), 4 is dropped (duplicate), 6 is dropped (out of range)
    assert len(state.filtered_expenses) == 3
    assert {e.id for e in state.filtered_expenses} == {"1", "3", "5"}
    
    # Check flags
    assert len(state.missing_data_flags) == 4
    problems = [f.problem for f in state.missing_data_flags]
    assert "Missing date" in problems
    assert "Missing amount" in problems
    assert "Duplicate" in problems
    assert "Unsupported Currency" in problems

def test_categorization_logic():
    state = ExpenseReportState(user_id="test")
    state.filtered_expenses = [
        Expense(id="1", date=date(2026, 7, 5), merchant="IndiGo Airlines", amount=100.0, currency="INR"),
        Expense(id="2", date=date(2026, 7, 5), merchant="Taj Hotel", amount=100.0, currency="INR"),
        Expense(id="3", date=date(2026, 7, 5), merchant="Starbucks", amount=100.0, currency="INR"),
        Expense(id="4", date=date(2026, 7, 5), merchant="Uber", amount=100.0, currency="INR"),
    ]
    
    # Temporarily bypass LLM logic for tests by using dummy if it hits the fallback
    state = categorization_node(state)
    
    assert len(state.categorized_expenses) == 4
    categories = {e.category for e in state.categorized_expenses}
    assert "Airfare" in categories
    assert "Lodging" in categories
    assert "Meals" in categories
    assert "Ground Transport" in categories

def test_calculation_logic():
    from app.state.blackboard import CategorizedExpense, DataQualityFlag
    state = ExpenseReportState(user_id="test")
    state.categorized_expenses = [
        CategorizedExpense(id="1", date=date(2026, 7, 5), merchant="A", amount=100.0, currency="INR", category="Meals"),
        CategorizedExpense(id="2", date=date(2026, 7, 5), merchant="B", amount=50.0, currency="INR", category="Meals"),
        CategorizedExpense(id="3", date=date(2026, 7, 5), merchant="C", amount=200.0, currency="INR", category="Lodging"), # Flagged
    ]
    state.missing_data_flags = [
        DataQualityFlag(expense_id="3", problem="Needs receipt", action_required="x", status="NEEDS_REVIEW")
    ]
    
    state = calculation_node(state)
    
    assert state.totals["confirmed_total"] == 150.0
    assert state.totals["Meals"] == 150.0
    assert state.provisional_totals["provisional_total"] == 200.0
