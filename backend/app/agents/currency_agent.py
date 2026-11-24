"""Currency Conversion Agent: a real tool-calling example (Unit III: Tools).

Runs only when a filtered expense is in a currency other than INR (the
project supports USD/EUR/GBP alongside INR; anything else is already
flagged "Unsupported Currency" upstream). It converts each foreign amount
to INR for display using `currency_tool.get_rate_to_inr`, which calls a
live exchange-rate API when reachable and a static table otherwise.

This is informational only: `converted_total_inr` is a separate field the
UI can show next to the mixed-currency note. It never feeds into
`totals["confirmed_total"]`, so the Review Agent's independent arithmetic
check is unaffected regardless of whether live rates were available.
"""
from app.state.blackboard import ExpenseReportState
from app.services.currency_tool import get_rate_to_inr


def currency_conversion_node(state: ExpenseReportState) -> ExpenseReportState:
    state.current_agent = "Currency Conversion"

    foreign_currencies = sorted({
        exp.currency.upper() for exp in state.filtered_expenses if exp.currency.upper() != "INR"
    })
    if not foreign_currencies:
        state.agent_status["Currency Conversion"] = "SKIPPED"
        state.run_log.append({
            "agent": "Currency Conversion",
            "action": "All expenses are already in INR; stage skipped.",
            "status": "SKIPPED",
        })
        return state

    state.agent_status["Currency Conversion"] = "RUNNING"

    conversions = {currency: dict(zip(("rate_to_inr", "source"), get_rate_to_inr(currency)))
                   for currency in foreign_currencies}

    converted_total = 0.0
    for exp in state.filtered_expenses:
        amount = exp.amount or 0.0
        currency = exp.currency.upper()
        rate = 1.0 if currency == "INR" else conversions[currency]["rate_to_inr"]
        converted_total += amount * rate

    state.currency_conversions = conversions
    state.converted_total_inr = round(converted_total, 2)

    rates_desc = ", ".join(
        f"1 {c} = INR {v['rate_to_inr']:.2f} ({v['source']})" for c, v in conversions.items()
    )
    state.agent_status["Currency Conversion"] = "COMPLETED"
    state.run_log.append({
        "agent": "Currency Conversion",
        "action": (
            f"Converted {len(foreign_currencies)} currenc{'y' if len(foreign_currencies) == 1 else 'ies'} "
            f"to INR for display: {rates_desc}. Informational total: INR {state.converted_total_inr:.2f}"
        ),
        "status": "COMPLETED",
    })
    return state
