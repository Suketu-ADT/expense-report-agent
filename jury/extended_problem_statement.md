# Extended Problem Statement: Autonomous Expense Reporting Agent
## Agentic AI Mini-Project Extension (Unit II, Unit III & Unit IV)

---

## 1. Original Problem Statement

Manual preparation, verification, and dispatch of business travel expense reports is a labor-intensive, error-prone workflow that burdens corporate travelers and finance departments alike. Employees frequently juggle fragmented receipts, inconsistent transaction logs, disparate merchant descriptions, multiple currencies, and missing critical fields (dates, amounts, receipt references). 

The original **Expense Report Agent** addressed this by establishing an autonomous, multi-agent pipeline using LangGraph, Python FastAPI, and React. The system parses unstructured user requests (e.g., *"Generate my travel expense report for June 2026 and email it to finance"*), ingests raw expense data, validates transactions, categorizes items using specialized rules/LLM classifiers, computes confirmed and provisional totals, generates formatted PDF reports, and handles email delivery.

While effective as a single-pass processing system, the initial baseline had three critical architectural limitations:
1. **Fixed, Non-Reasoning Execution Plan:** The Orchestrator always ran the exact same eight-stage sequence regardless of what the user actually asked for. A request like "flag anything over ₹5000" or "compare this to last month" had no effect — the words were read only far enough to extract a month and year.
2. **Stateless Execution (Lack of Memory):** Every agent run was ephemeral. The agent retained no recollection of previously filed reports, historical spending trends, or user preferences once the graph run completed.
3. **Lack of Independent Multi-Agent Review & Fault Recovery:** Calculations and categorizations produced by specialist agents were assumed correct. The pipeline had no mechanism for independent verification, cross-agent correction requests, bounded retry loops, or human escalation before final report dispatch.

---

## 2. Unit II Extension: Planning & Reasoning

To replace the fixed sequence with an execution plan that actually reflects the request, the Orchestrator was extended with a **Planner** (`app/services/planner_service.py`):

- **Deterministic keyword/regex pass (always runs, fully offline):** extracts an anomaly-flagging threshold (e.g. "flag anything over 2000") and a comparison request (e.g. "compare it to last month") directly from the request text, in addition to the existing month/year extraction.
- **LLM refinement pass (when `GROQ_API_KEY` is configured):** re-reads the same request text and returns a structured JSON intent (`anomaly_threshold`, `compare_to_previous`), refining phrasing the regex rules do not anticipate. If the LLM call fails or returns something unparseable, the deterministic result from the first pass stands untouched — the planner never degrades below its offline baseline.
- **The resulting `RequestIntent` decides the plan**, not just the data: the Orchestrator builds `state.execution_plan` by inserting an **Anomaly Detection** stage when a threshold was requested and a **Period Comparison** stage when a comparison was requested, and logs which planning mode (`deterministic` or `llm`) produced the plan.
- **Two new specialist agents consume the intent** without ever touching totals or categories, so the Expense Review Agent's independent arithmetic recheck (Unit IV) is unaffected by whichever optional stages ran:
  - `Anomaly Detection` (`app/agents/anomaly_agent.py`) flags categorized expenses above the requested threshold (`is_anomaly=True`), read-only with respect to totals.
  - `Period Comparison` (`app/agents/comparison_agent.py`) recalls the previous period's confirmed total from persistent memory (Unit III) and reports the delta, or reports plainly that no prior report exists.
- Both stages always appear in `agent_status` (as `COMPLETED` or `SKIPPED`), so the dashboard's Agent Pipeline view and run log show *why* a stage did or didn't run — the same transparency pattern already used for the Correction stage's "Not needed" state.

This is a deliberately conservative form of dynamic planning: the underlying LangGraph topology stays fixed and auditable (a hard requirement for a financial pipeline), but *which* stages do meaningful work, and the shape of `execution_plan` shown to the user, now follows from reasoning over the request rather than a hardcoded list.

---

## 3. Unit III Extension: Persistent Memory & Tool-Environment Interaction

To address statelessness, the system was extended with a dual-tier memory architecture adhering to Unit III Agentic AI principles:

### A. Short-Term Working Memory (Blackboard State)
- Implemented via a shared, mutable Pydantic blackboard (`ExpenseReportState`) passed along the LangGraph execution flow.
- Holds transient working context: user instructions, resolved date ranges, raw and filtered transactions, active data quality flags, category subtotal allocations, execution logs, and pending correction tasks.

### B. Long-Term Persistent Memory (SQLite / SQLAlchemy)
- **Report History Store (`ReportHistoryModel`):** Persists full report summaries across runs and server restarts. Records include report IDs (`RPT-XXXXXXXX`), period labels, confirmed grand totals, provisional totals, category breakdowns, flagged item counts, duplicate exclusion counts, and delivery statuses.
- **User Preference Store (`UserPreferenceModel`):** Retains persistent user configurations (e.g., default currency, notification rules, category preferences).
- **Proactive Memory Recall:** At execution start, the `Orchestrator` queries persistent memory for existing reports matching the requested billing period, informing subsequent planning decisions.

### C0. Report Cache (Write-Through, In Front of SQLite)

Report history is read far more often than it's written: every run's
Orchestrator recalls prior reports for the period, the Period Comparison
stage looks up the previous period's total, and the dashboard polls
`/api/reports/history` repeatedly while a run is live — each of those was
previously a fresh SQLite query every time.

`memory_service.py` now keeps three in-memory caches (by `report_id`, by
`(period_label, user_id)`, and by `user_id` for the full list) in front of
the database, following the same plain-module-dict pattern `main.active_runs`
already uses for live run state rather than adding a new caching
dependency. Every write — `save_report_summary`, and the two places that
update a report directly via SQLAlchemy (`approve_run`'s delivery-status
flip, and the PDF-regeneration path's `report_file_path` update) — refreshes
the cache immediately, so **a cached read is never stale**. Each getter
also returns a shallow copy rather than the cached object itself, since one
caller (`GET /api/reports/{id}`) mutates what it gets back by adding a
`reimbursement` key — without the copy, that mutation would have leaked
into the cache and corrupted every later reader.

This was verified live: fetching a report, approving it (which flips
`delivery_status` via the bypass path), and fetching it again correctly
shows `pending` → `delivered` with no network/DB round trip needed for the
read itself — plus the existing 82 backend tests and the 500-claim
large-dataset regression, both re-run after this change and still
reporting 100%.

### C. Tool Use: Retrieval-Augmented Policy Grounding

The reimbursement engine previously justified every decision with one hardcoded string (`"Meal limit INR 800.00"`). It now treats the company travel policy (`data/policy/travel_policy.md`) as a tool it queries, via `app/services/policy_rag.py`:

- The policy document is chunked by section at import time (`## 2.1 Meals`, `## 2.2 Lodging`, …).
- Each reimbursement decision queries the chunk store with the expense's category and retrieves the single best-matching clause using a local term-overlap retriever — no embedding model and no network call, so the project's 100% offline guarantee is preserved.
- The retrieved clause's section number and heading become a citation (e.g. *"Travel Policy §2.1 Meals: capped at INR 800.00 per claim"*) attached to `item["reason"]` and `item["policy_citation"]`, which the existing reviewer UI and PDF already render — no frontend changes were needed.
- This only grounds the *explanation*; it does not change which amount is approved. The underlying cap arithmetic is untouched, and the full 500-claim `ExpenseFlow-Large-Dataset` regression (`run_test.py`) was re-run end-to-end and still reports `"result": "passed"` against every expected value.
- If the on-disk policy file is unreachable (e.g. a deployment that packages only `app/`), the service falls back to an embedded copy of the same text — the same "never degrade below the offline baseline" pattern already used for the categorization LLM fallback.

---

## 4. Unit IV Extension: Multi-Agent Collaboration, Review & Fault Recovery

To ensure financial accuracy and system robustness, the pipeline was upgraded with an independent review, verification, and recovery loop adhering to Unit IV Multi-Agent Systems:

### A. Expense Review Agent (Specialist Verifier)
- Operates independently from the calculation and categorization agents using deterministic Python logic (avoiding non-deterministic LLM arithmetic for financial sums).
- Performs five mandatory integrity checks:
  1. Confirmed total reconciliation with eligible (non-flagged) expenses.
  2. Verification that duplicate transactions have been strictly excluded from totals.
  3. Detection of missing required fields (dates, amounts, currencies) that were left unflagged.
  4. Category subtotal cross-footing and reconciliation with grand totals.
  5. Consistency verification between calculation state and generated PDF artifacts.

### B. Structured Inter-Agent Communication (`AgentMessage`)
- When discrepancies or data defects are detected, the Review Agent issues structured messages containing:
  - `sender` & `recipient` IDs
  - `message_type`: `"correction_request"`, `"correction_result"`, `"info"`
  - `findings`: structured error specifics and severity (`critical`, `warning`)
  - `requested_action`: deterministic instruction for remediation

### C. Self-Healing Correction Loop & Bounded Retries
- The `Correction Agent` receives structured requests, applies deterministic recalculations, strips duplicate inclusions, updates flags, and sends back `correction_result` messages.
- LangGraph routes execution through a conditional loop (`Expense Review` → `Correction` → `Re-Review`).
- Retries are strictly bounded by `max_retries = 3`.

### D. Human-in-the-Loop Escalation & Dispatch Gating
- If critical discrepancies persist beyond the retry ceiling or unfixable inconsistencies occur, the pipeline sets `needs_human_review = True` and holds email dispatch.
- Reports require explicit human approval via the frontend dashboard or API before final dispatch occurs.

---

## 4b. Further Extensions: Reasoning, Autonomy, Tools and Guardrails

Four smaller, independently-scoped extensions, each kept additive so none
of them could silently change a reconciled total or an approval decision:

- **Reflection on the categorization LLM fallback** (`llm_service.categorize_with_reflection`,
  wired into `categorization_agent.py`): a first pass proposes a category,
  a second pass critiques that specific proposal and may revise it, and
  the critique is written to the run log either way. Skipped entirely
  (returning the first pass unchanged) when no API key is set or the first
  pass already fell back to Uncategorized. Example from a real run:
  `"Domino's" → Meals, reflection: "Domino's sells food; large amount
  suggests catering, but still falls under meals."` — confirmed, not
  revised, but the reasoning is now visible rather than opaque.
- **Configurable autonomy level** (`autonomy_level`: `cautious` / `co_pilot`
  / `trusting`, set per request): changes how much the Correction loop is
  trusted before escalating — `cautious` sets `max_retries=0` and escalates
  on *any* review finding including warnings; `co_pilot` is the original
  behavior (3 retries, only unresolved critical findings escalate);
  `trusting` allows 5 retries. **Email dispatch still always requires
  explicit human approval in every level** — see jury/ethics_and_compliance.md
  for why that one gate never becomes configurable.
- **Multi-agent debate for ambiguous receipt matches** (`llm_service.debate_receipt_match`,
  called from `exception_resolution_agent.py`): when exactly two receipt
  candidates share a claim's merchant and date, two LLM advocates each
  argue for one candidate and a judge opines — but this is **advisory
  only**. The claim still always escalates to a human exactly as before;
  the debate transcript is attached to the decision purely as extra
  context the reviewer sees in "Last receipt batch." (An earlier version
  let the judge's pick actually resolve the claim; it was reverted after
  it silently changed a labelled test's outcome — a concrete demonstration
  of why probabilistic output stays advisory on anything money-adjacent.)
- **Currency Conversion tool** (`currency_tool.get_rate_to_inr`, called from
  a new `Currency Conversion` graph stage): a genuine external tool call —
  a live, no-auth exchange-rate API with a 3-second timeout — converts
  foreign-currency claims (USD/EUR/GBP) to INR for display, falling back to
  a static, clearly-labelled rate table when the API is unreachable. This
  is informational only (`converted_total_inr`); it never feeds into
  `totals["confirmed_total"]`.

## 5. Updated Objectives

1. **Autonomous Financial Pipeline:** Maintain end-to-end processing from natural language prompt to formatted PDF report.
2. **Request-Driven Planning:** Derive which optional stages a run needs from the user's actual wording, rather than always executing an identical fixed sequence.
3. **Persistent Contextual Memory:** Ensure memory persists across backend restarts and allows instant historical inspection.
4. **Deterministic Independent Verification:** Eliminate calculation drift and undetected duplicates via a specialized Review Agent.
5. **Self-Healing Agent Collaboration:** Demonstrate autonomous error detection, inter-agent structured messaging, and automated remediation.
6. **Fail-Safe Human Control:** Enforce human approval gates prior to external transmission when issues are flagged.

---

## 6. System Scope

- **Supported Inputs:** Natural language text prompts + CSV expense datasets.
- **Data Entities:** Travel expenses including Airfare, Lodging, Meals, Ground Transport, and Miscellaneous.
- **Storage:** Local SQLite database with ACID compliance, ensuring 100% offline feasibility.
- **Interfaces:** Modern React dark-mode dashboard (with real-time pipeline status, interactive tables, charts, review panels, and memory inspection) + FastAPI REST endpoints.

---

## 7. Expected Outcomes

- Zero manual effort for monthly expense aggregation while maintaining 100% mathematical auditability.
- Clear visual proof of request-driven planning, multi-agent collaboration, inter-agent messaging, and self-healing recovery during jury evaluation.
- Seamless offline operation suitable for collegiate jury presentation without internet dependency.
