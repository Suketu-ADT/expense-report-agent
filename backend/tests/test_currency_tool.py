from datetime import date

from app.agents.currency_agent import currency_conversion_node
from app.services.currency_tool import get_rate_to_inr
from app.state.blackboard import Expense, ExpenseReportState


def test_inr_short_circuits_without_a_network_call():
    rate, source = get_rate_to_inr("INR")
    assert rate == 1.0
    assert source == "live"


def test_unreachable_api_falls_back_to_the_static_table(monkeypatch):
    import app.services.currency_tool as currency_tool

    def boom(*args, **kwargs):
        raise ConnectionError("no network in this test")

    monkeypatch.setattr(currency_tool.requests, "get", boom)
    rate, source = get_rate_to_inr("USD")
    assert rate == currency_tool.FALLBACK_RATES_TO_INR["USD"]
    assert source == "offline-fallback"


def test_currency_conversion_skips_when_everything_is_already_inr():
    state = ExpenseReportState(user_id="test")
    state.filtered_expenses = [
        Expense(id="1", date=date(2026, 7, 1), merchant="A", amount=100.0, currency="INR"),
    ]
    state = currency_conversion_node(state)
    assert state.agent_status["Currency Conversion"] == "SKIPPED"
    assert state.currency_conversions is None


def test_currency_conversion_converts_foreign_amounts(monkeypatch):
    import app.services.currency_tool as currency_tool
    monkeypatch.setattr(currency_tool.requests, "get", lambda *a, **k: (_ for _ in ()).throw(ConnectionError()))

    state = ExpenseReportState(user_id="test")
    state.filtered_expenses = [
        Expense(id="1", date=date(2026, 7, 1), merchant="A", amount=100.0, currency="INR"),
        Expense(id="2", date=date(2026, 7, 1), merchant="B", amount=10.0, currency="USD"),
    ]
    state = currency_conversion_node(state)
    assert state.agent_status["Currency Conversion"] == "COMPLETED"
    assert state.currency_conversions["USD"]["source"] == "offline-fallback"
    expected_total = 100.0 + 10.0 * currency_tool.FALLBACK_RATES_TO_INR["USD"]
    assert state.converted_total_inr == round(expected_total, 2)
