# Extended Problem Statement: Autonomous Expense Reporting Agent
## Agentic AI Mini-Project Extension (Unit III & Unit IV)

---

## 1. Original Problem Statement

Manual preparation, verification, and dispatch of business travel expense reports is a labor-intensive, error-prone workflow that burdens corporate travelers and finance departments alike. Employees frequently juggle fragmented receipts, inconsistent transaction logs, disparate merchant descriptions, multiple currencies, and missing critical fields (dates, amounts, receipt references). 

The original **Expense Report Agent** addressed this by establishing an autonomous, multi-agent pipeline using LangGraph, Python FastAPI, and React. The system parses unstructured user requests (e.g., *"Generate my travel expense report for June 2026 and email it to finance"*), ingests raw expense data, validates transactions, categorizes items using specialized rules/LLM classifiers, computes confirmed and provisional totals, generates formatted PDF reports, and handles email delivery.

While effective as a single-pass processing system, the initial baseline had two critical architectural limitations:
1. **Stateless Execution (Lack of Memory):** Every agent run was ephemeral. The agent retained no recollection of previously filed reports, historical spending trends, or user preferences once the graph run completed.
2. **Lack of Independent Multi-Agent Review & Fault Recovery:** Calculations and categorizations produced by specialist agents were assumed correct. The pipeline had no mechanism for independent verification, cross-agent correction requests, bounded retry loops, or human escalation before final report dispatch.

---

## 2. Unit III Extension: Persistent Memory & Tool-Environment Interaction

To address statelessness, the system was extended with a dual-tier memory architecture adhering to Unit III Agentic AI principles:

### A. Short-Term Working Memory (Blackboard State)
- Implemented via a shared, mutable Pydantic blackboard (`ExpenseReportState`) passed along the LangGraph execution flow.
- Holds transient working context: user instructions, resolved date ranges, raw and filtered transactions, active data quality flags, category subtotal allocations, execution logs, and pending correction tasks.

### B. Long-Term Persistent Memory (SQLite / SQLAlchemy)
- **Report History Store (`ReportHistoryModel`):** Persists full report summaries across runs and server restarts. Records include report IDs (`RPT-XXXXXXXX`), period labels, confirmed grand totals, provisional totals, category breakdowns, flagged item counts, duplicate exclusion counts, and delivery statuses.
- **User Preference Store (`UserPreferenceModel`):** Retains persistent user configurations (e.g., default currency, notification rules, category preferences).
- **Proactive Memory Recall:** At execution start, the `Orchestrator` queries persistent memory for existing reports matching the requested billing period, informing subsequent planning decisions.

---

## 3. Unit IV Extension: Multi-Agent Collaboration, Review & Fault Recovery

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

## 4. Updated Objectives

1. **Autonomous Financial Pipeline:** Maintain end-to-end processing from natural language prompt to formatted PDF report.
2. **Persistent Contextual Memory:** Ensure memory persists across backend restarts and allows instant historical inspection.
3. **Deterministic Independent Verification:** Eliminate calculation drift and undetected duplicates via a specialized Review Agent.
4. **Self-Healing Agent Collaboration:** Demonstrate autonomous error detection, inter-agent structured messaging, and automated remediation.
5. **Fail-Safe Human Control:** Enforce human approval gates prior to external transmission when issues are flagged.

---

## 5. System Scope

- **Supported Inputs:** Natural language text prompts + CSV expense datasets.
- **Data Entities:** Travel expenses including Airfare, Lodging, Meals, Ground Transport, and Miscellaneous.
- **Storage:** Local SQLite database with ACID compliance, ensuring 100% offline feasibility.
- **Interfaces:** Modern React dark-mode dashboard (with real-time pipeline status, interactive tables, charts, review panels, and memory inspection) + FastAPI REST endpoints.

---

## 6. Expected Outcomes

- Zero manual effort for monthly expense aggregation while maintaining 100% mathematical auditability.
- Clear visual proof of multi-agent collaboration, inter-agent messaging, and self-healing recovery during jury evaluation.
- Seamless offline operation suitable for collegiate jury presentation without internet dependency.
