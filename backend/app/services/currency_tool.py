"""Currency conversion tool: a genuine external tool call (not hardcoded
arithmetic) that the Currency Conversion agent uses to express foreign
claims in INR for display.

This addresses a documented limitation: amounts in different currencies
were summed as-is with no conversion, only a "mixed currencies" flag. It
tries a live, no-auth exchange-rate API first, with a short timeout, and
falls back to a static rate table — clearly labelled as such — when the
network call fails. That keeps the project's offline-capable guarantee:
the conversion is informational only and is never substituted into the
reconciled `confirmed_total` the Review Agent checks.
"""
from typing import Tuple

import requests

FALLBACK_RATES_TO_INR = {"USD": 83.0, "EUR": 90.0, "GBP": 105.0}
_API_URL = "https://open.er-api.com/v6/latest/{base}"
_TIMEOUT_SECONDS = 3


def get_rate_to_inr(currency: str) -> Tuple[float, str]:
    """Return (rate, source) for converting 1 unit of `currency` to INR.
    `source` is "live" when the API call succeeded, "offline-fallback"
    otherwise (network error, timeout, or the currency isn't in the live
    response — then the static table is used)."""
    currency = currency.upper()
    if currency == "INR":
        return 1.0, "live"
    try:
        response = requests.get(_API_URL.format(base=currency), timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        rate = response.json().get("rates", {}).get("INR")
        if rate:
            return float(rate), "live"
    except Exception:
        pass
    return FALLBACK_RATES_TO_INR.get(currency, 1.0), "offline-fallback"
