# Autonomous Expense Reporting Agent
## Multi-Agent AI System with Persistent Memory & Self-Healing Review
**Agentic AI Jury Presentation (Units III & IV Extension)**

---

## Slide 1: Original Problem Statement & Baseline Architecture

### The Problem
- Manual business expense reporting is tedious, fragmented, and vulnerable to arithmetic inaccuracies, missed receipts, and duplicate claims.
- Corporate finance teams spend hundreds of hours auditing monthly reimbursement submissions.

### The Baseline System
- **Framework:** LangGraph state graph with Python FastAPI backend and React frontend.
- **Specialist Agents:** Orchestrator, Data Retrieval, Filter & Validation, Categorization, Calculation, Report Generation, and Email Dispatch.
- **Shared State:** Pydantic Blackboard State (`ExpenseReportState`) storing transient execution artifacts.
- **Limitation:** Stateless execution (no retention across runs) and single-pass pipeline without verification or recovery mechanisms.

---

## Slide 2: Unit III — Memory, Tools & Environment Interaction

### Dual-Tier Memory Architecture
1. **Short-Term Working Memory (Blackboard State):**
   - Transmits live context across nodes: date range, raw expenses, data quality flags, category allocations, and inter-agent messages.
2. **Long-Term Persistent Memory (SQLite / SQLAlchemy):**
   - **`ReportHistoryModel`:** Persists finalized report summaries (`report_id`, period, confirmed/provisional totals, category breakdown, review findings, delivery status).
   - **`UserPreferenceModel`:** Retains user configurations (default currency, notification preferences) across sessions.
   - **`AgentMessageModel`:** Audit log of all structured inter-agent communication.

### Proactive Memory Recall
- The Orchestrator inspects SQLite memory at graph inception.
- Recalls past reports for the requested billing cycle to prevent redundant filings and inform planning.
- **Durability:** Survives server restarts; accessible offline with zero cloud dependency.

---

## Slide 3: Unit IV — Multi-Agent Collaboration & Review Loop

### Independent Expense Review Agent
- Acts as an autonomous quality auditor separate from calculation and categorization nodes.
- Utilizes deterministic Python arithmetic (eliminating LLM hallucination for financial calculations).
- **Core Verifications:**
  1. Grand total cross-check against eligible expense items.
  2. Strict verification of duplicate transaction exclusions.
  3. Detection of missing mandatory fields (date, amount) left unflagged.
  4. Category subtotal cross-footing against confirmed totals.
  5. Artifact consistency between calculation models and generated PDF files.

### Structured Inter-Agent Communication (`AgentMessage`)
- Exchanges typed messages (`sender`, `recipient`, `message_type`, `findings`, `requested_action`).
- When errors occur, sends a `correction_request` to the responsible agent.

### Self-Healing Feedback Loop & Bounded Retries
- `Correction Agent` implements requested remediation and sends a `correction_result`.
- LangGraph conditional edges route execution through `Expense Review` → `Correction` → `Re-Review`.
- Enforces `max_retries = 3` to prevent infinite oscillation.

### Human-in-the-Loop Gate
- Critical unresolvable issues escalate to `needs_human_review = True`, automatically holding email dispatch until explicit reviewer approval is granted.

---

## Slide 4: Live Demonstration & Failure Recovery Trace

### Demonstration Scenarios
1. **Scenario 1: Happy Path Execution & Memory Persistence**
   - User inputs: *"Generate my travel expense report for June 2026 and email it to finance"*.
   - 20 expenses parsed, categorized, audited, and exported to PDF.
   - Memory Persistence Agent stores report as `RPT-XXXXXXXX`.
   - Report History table immediately populates and persists across page reloads.

2. **Scenario 2: Injected Fault & Self-Healing Recovery**
   - Checkbox enabled: *"Unit IV Demo: Inject calculation discrepancy"*.
   - Calculation agent state is perturbed by phantom ₹500.
   - **Execution Trace:**
     ```
     [Calculation] -> Reported Confirmed Total: ₹66,150.00
     [Expense Review] -> CRITICAL MISMATCH: Calculated ₹65,650 vs Reported ₹66,150
     [Expense Review] -> Dispatches AgentMessage to Correction Agent
     [Correction] -> Applies deterministic recalculation from categorized records
     [Re-Review] -> Audits corrected totals: 0 findings -> Status: PASSED
     [Report Generation] -> Generates clean PDF artifact
     [Memory Persistence] -> Commits verified report to SQLite
     [Email Dispatch] -> Dispatches report
     ```

3. **Scenario 3: Human Approval Gate**
   - When issues require review, email dispatch is halted. Reviewer reviews audit findings in the UI and clicks **Approve & Dispatch Email**.

---

## Slide 5: Results, Engineering Rigor & Conclusion

### Summary of Achievements
- **25 / 25 Automated Tests Passing (100% Pass Rate):**
  - Unit III Persistent Memory (session persistence, empty-state resilience, preference storage).
  - Unit IV Collaboration (total reconciliation, duplicate detection, message exchange, discrepancy detection, retry bounding, human approval gating).
- **Zero Architecture Regression:** Original frontend layout, styling, and existing agent nodes 100% preserved.
- **Offline Reliability:** Operates entirely locally with SQLite, mocked/simulated SMTP, and deterministic Python validation.

### Key Takeaway for the Jury
This project elevates a simple procedural pipeline into a true **Agentic AI system** featuring:
- **Stateful Intelligence:** Remembering past history across restarts.
- **Multi-Agent Collaboration:** Specialization, structured messaging, and peer review.
- **Robust Fault Tolerance:** Autonomous detection and self-healing recovery before human escalation.
