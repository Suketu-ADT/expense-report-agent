from app.services.policy_rag import retrieve_clause
from app.services.reimbursement import PolicyOptions, create_sheet, edit_item, ItemEdit
from app.state.blackboard import ExpenseReportState, CategorizedExpense


def test_retrieve_clause_matches_category_heading():
    assert retrieve_clause("Meals").section == "2.1"
    assert retrieve_clause("Lodging").section == "2.2"
    assert retrieve_clause("Ground Transport").section == "2.3"
    assert retrieve_clause("Airfare").section == "2.4"
    assert retrieve_clause("Other / Uncategorized").section == "2.5"


def test_retrieve_clause_always_returns_a_result():
    clause = retrieve_clause("")
    assert clause.text
    assert clause.citation.startswith("Travel Policy")


def test_reimbursement_decision_cites_the_retrieved_clause():
    claim = CategorizedExpense(id="M1", merchant="Campus Cafe", date="2026-07-10",
                                amount=600, category="Meals", currency="INR")
    sheet = create_sheet(ExpenseReportState(user_id="test", categorized_expenses=[claim]), PolicyOptions())
    receipt = "Merchant: Campus Cafe\nDate: 2026-07-10\nTotal: INR 600"
    edit_item(sheet, 0, ItemEdit(revision=0, action="attach", text=receipt))
    item = sheet["items"][0]
    assert item["status"] == "eligible"
    assert item["approved"] == 60000
    assert item["policy_citation"] == "Travel Policy §2.1 Meals"
    assert "2.1 Meals" in item["reason"]


def test_reimbursement_cap_math_is_unchanged_by_citation(monkeypatch):
    claim = CategorizedExpense(id="M2", merchant="Campus Cafe", date="2026-07-10",
                                amount=2000, category="Meals", currency="INR")
    sheet = create_sheet(ExpenseReportState(user_id="test", categorized_expenses=[claim]), PolicyOptions(meal_cap=800))
    receipt = "Merchant: Campus Cafe\nDate: 2026-07-10\nTotal: INR 2000"
    edit_item(sheet, 0, ItemEdit(revision=0, action="attach", text=receipt))
    item = sheet["items"][0]
    assert item["eligible"] == 80000
    assert "2.1 Meals" in item["reason"]
