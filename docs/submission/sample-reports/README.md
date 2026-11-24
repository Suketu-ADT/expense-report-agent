# ExpenseFlow AI — 10 sample reports

Ten scenarios, each driven end-to-end through the **real, running backend**
(CSV import → `/api/run` → receipt matching → PDF export) — nothing here is
hand-written or mocked. Each `NN-name.pdf` is 2–3 pages and is paired with:

- `NN-name.claims.csv` — the CSV to import to reproduce it,
- `NN-name/receipts/*.txt` — the exact receipt text files to upload in
  **Match uploaded receipts** (same content the script fed to the API),
- `NN-name_status.json` — a snapshot of the full `/api/run/{id}` response
  (agent statuses, run log, planner intent, review result, trace).

Amounts are in INR unless a row's `currency` column says otherwise. All
claims fall in **July 2026** (the app's current "last month") unless noted.

All ten PDFs use ExpenseFlow AI's letterhead template (`backend/app/services/pdf_service.py`) — a branded header band, report metadata block, color-coded claim status badges, and a numbered footer — so they read as a real corporate report rather than a plain data dump.

A June 2026 baseline run — [`00-baseline-june-2026.claims.csv`](00-baseline-june-2026.claims.csv), no receipts needed, not a numbered report itself — was replayed first so Period Comparison (#04, #05) has a prior month in memory to recall. Its confirmed total is ₹32,190.00.

## Reproduce any of them

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then, with the server running, re-import a scenario's `claims.csv` via
`POST /api/expenses/import` (or drag it into the Overview page's CSV
uploader), start a run with that scenario's request text and policy
settings from the table below, and — for scenarios that mention receipts —
upload the matching receipt text through **Review claim decisions ->
Match uploaded receipts**. The `_status.json` file for each scenario shows
exactly what the response should look like.

## The 10 reports

| # | Report | What it demonstrates | Request text | Notes |
|---|---|---|---|---|
| 01 | [Multi-category RAG policy grounding](01-multi-category-rag-policy.pdf) | Reimbursement decisions cite the actual travel-policy document (`travel_policy.md`) across Airfare, Lodging, Meals, Ground Transport and Other — not a hardcoded string | "Generate my travel expense report for July 2026 and email it to finance." | 14 claims, 2 meals land above the ₹800 cap and show the capped citation |
| 02 | [Anomaly detection](02-anomaly-detection.pdf) | The Planner parses a threshold out of free text and the Anomaly Detection stage flags every expense over it | "...and flag anything over 5000." | 12 claims; several flights/hotels legitimately exceed ₹5,000 and are flagged |
| 03 | [Multi-currency conversion](03-multi-currency-conversion.pdf) | Tool use: live USD/EUR/GBP → INR conversion rates fetched for a mixed-currency trip; informational only, never changes the reimbursement decision | "...for the Singapore-Frankfurt-London client trip." | 12 claims across 4 currencies; foreign-currency claims are correctly held ("Outside INR policy") while INR claims clear |
| 04 | [Period comparison — memory recall](04-period-comparison-memory-recall.pdf) | Long-term memory: the Orchestrator recalls the previous month's confirmed total from SQLite and computes a real delta | "...and compare it to last month." | Needs the June 2026 baseline run first; shows ₹32,190.00 → ₹41,200.00 (+27.99%) |
| 05 | [Combined dynamic planning (flagship)](05-combined-dynamic-planning.pdf) | All three optional Unit II/III stages — Anomaly Detection, Period Comparison, Currency Conversion — triggered together from one free-form request | "...flag anything over 6000, and compare it to last month." | 10 claims, one foreign-currency leg, one outlier |
| 06 | [Multi-agent debate — ambiguous receipt](06-multi-agent-debate-ambiguous-receipt.pdf) | Two LLM advocates argue for competing receipt candidates and a judge opines — purely advisory; the claim still stays held for a human | plain July 2026 request | 11 claims; `S6-03` has two candidate receipts for one claim, see its `agent_review.debate` in the status JSON |
| 07 | [Receipt reuse / duplicate-claim guard](07-receipt-reuse-duplicate-claim-guard.pdf) | Two distinct claims share one merchant+date; a single submitted receipt is never auto-attached to either — both stay held | plain July 2026 request | 11 claims; `S7-03`/`S7-04` both escalate instead of guessing |
| 08 | [Guardrails & data-quality](08-guardrails-data-quality.pdf) | Missing date, missing amount, duplicate row, unsupported currency (JPY), and a prompt-injection probe in a merchant field — all caught; the injection attempt is sanitized before the LLM sees it and still lands in "Other / Uncategorized", not the category it tried to force | plain July 2026 request | 12 claims; see the Categorization `WARNING` log line in the status JSON |
| 09 | [Autonomy levels — cautious / co-pilot / trusting](09-autonomy-levels-contrast.pdf) | The same 10 claims run three times under each configurable autonomy level; `max_retries` is 0 / 3 / 5 respectively (see the three companion `_cautious` / `_co_pilot` / `_trusting` JSON files) | plain July 2026 request | PDF shown is the co-pilot run; all three reviews happened to pass cleanly on this clean data |
| 10 | [Comprehensive flagship demo](10-comprehensive-flagship-demo.pdf) | One larger, realistic run touching every category, a foreign-currency leg, an anomaly, a capped meal, and a missing-date flag — the single report to lead with if you only show one | "...flag anything over 7000, and email it to finance." | 14 claims |

## Where these fit in the submission

These are demo material for the jury (checklist item 4: "screenshots, test
results and demo video"), complementary to the five smaller receipt-focused
walkthroughs in `expenseflow-sample-reports/` at the repository root, which
focus specifically on receipt-evidence edge cases (exact match, mismatch,
reuse, ambiguity, OCR correction) rather than the Unit II–IV extensions
these ten cover.
