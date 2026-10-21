# Agentic AI Viva Voce Preparation Guide
## Units III & IV: Memory, Tools & Multi-Agent Systems

This document contains likely technical and architectural questions a university examination jury will ask regarding the Expense Report Agent, paired with concise, authoritative answers.

---

### Q1: Why is memory required in an autonomous agent system?
**Answer:**  
Standard LLM or workflow executions are stateless: once a prompt finishes execution, all internal state is lost. In real-world enterprise applications, memory is necessary to:
1. Provide historical context (e.g., has an expense report for June 2026 already been filed?).
2. Support user personalization and policy compliance (remembering user currency preferences, reimbursement rules).
3. Enable cross-session auditing and compliance review without re-executing expensive processing pipelines.
4. Prevent duplicate disbursements or redundant email deliveries.

---

### Q2: What is the architectural difference between short-term memory and long-term memory in this application?
**Answer:**  
- **Short-Term Working Memory:** Implemented as a **Pydantic Blackboard State (`ExpenseReportState`)**. It lives only during the execution lifetime of the LangGraph graph. It carries transient runtime data—raw CSV records, validated lists, interim subtotal calculations, data quality flags, and active inter-agent correction requests.
- **Long-Term Persistent Memory:** Implemented using **SQLite with SQLAlchemy ORM (`ReportHistoryModel`, `UserPreferenceModel`, `AgentMessageModel`)**. It persists on physical disk across application restarts, server reboots, and browser reloads. It stores finalized report summaries, historical totals, and inter-agent communication audit logs.

---

### Q3: Why did you use LangGraph instead of simple chain-of-thought prompting or a standard sequential script?
**Answer:**  
1. **Cycles and Feedback Loops:** Sequential chains (like standard LangChain or linear scripts) cannot natively handle iterative recovery loops where an agent's output is audited and conditionally looped back for correction. LangGraph provides first-class support for cyclical graphs (`StateGraph`) with conditional routing edges.
2. **Deterministic State Synchronization:** LangGraph enforces a single source of truth (the Blackboard state), ensuring every specialist agent reads validated upstream data and writes structured mutations.
3. **Fault Tolerance & Branching:** Conditional edge functions (`check_review`, `check_validation`, `check_after_persist`) dynamically route execution based on runtime conditions (e.g., routing to `Correction` on error vs. `Report Generation` on pass, or halting at human review gates).

---

### Q4: How do the agents communicate with each other?
**Answer:**  
Agents communicate through two complementary patterns:
1. **Blackboard Pattern (Shared State):** All agents inspect and update the common typed Pydantic state (`ExpenseReportState`), reducing point-to-point coupling.
2. **Direct Structured Messaging (`AgentMessage`):** For targeted interactions like audit corrections, the Review Agent constructs an explicit, typed `AgentMessage` object detailing the sender (`Expense Review`), recipient (`Calculation`), message type (`correction_request`), specific findings (severity, discrepancy details), and required remediation. This creates a transparent, auditable communication trail stored in both working memory and persistent SQLite storage.

---

### Q5: How do review and financial reconciliation work? Why didn't you use an LLM for the Review Agent?
**Answer:**  
The **Expense Review Agent uses 100% deterministic Python arithmetic (using Python's `Decimal` module)** rather than an LLM.
- **Why avoid LLMs for financial arithmetic:** LLMs are probabilistic autoregressive models prone to token hallucination, rounding inaccuracies, and arithmetic drift. Financial auditing requires absolute precision and reproducibility.
- **How reconciliation works:** The Review Agent independently iterates over the `categorized_expenses`, filters out any IDs present in the `missing_data_flags` (such as excluded duplicates or unresolved items), computes its own confirmed grand total and category subtotals, and verifies that `recalc_total == state.totals['confirmed_total']`. If any mismatch or unflagged invalid field is detected, a structured finding is flagged.

---

### Q6: How does autonomous failure recovery work when an error is detected?
**Answer:**  
1. The **Expense Review Agent** detects a discrepancy (e.g., total mismatch or unexcluded duplicate).
2. It sets `review_result.overall_status = "needs_correction"` and appends an `AgentMessage` with `requested_action`.
3. The conditional routing edge `check_review` inspects `state.retry_count`. Since `retry_count < max_retries (3)`, it directs flow to the **Correction Agent**.
4. The Correction Agent parses the finding, applies deterministic recalculations, strips invalid records, marks findings as `resolved`, and increments `retry_count`.
5. Flow routes to **Re-Review**. If the recalculation passes, the review status becomes `passed` and graph execution resumes normally toward report generation.
6. If the error cannot be auto-corrected or exceeds 3 retries, the system escalates by marking `needs_human_review = True`.

---

### Q7: How are duplicate expenses detected and handled?
**Answer:**  
In `Filter & Validation Agent`, transactions are indexed by a composite fingerprint `(date, merchant, amount, currency)`. 
- When an identical fingerprint is detected, subsequent entries are excluded from `filtered_expenses` and flagged in `missing_data_flags` with `status = "EXCLUDED"` and `problem = "Duplicate"`.
- The **Expense Review Agent** independently verifies that no expense with `status = "EXCLUDED"` exists in the final `categorized_expenses` array. If an excluded item is found, it issues a `critical` finding to strip it and recalculate.

---

### Q8: How is human approval enforced before email dispatch?
**Answer:**  
Human-in-the-loop governance is enforced at the graph architecture level:
- In `expense_graph.py`, the conditional edge `check_after_persist` executes before the `Email Dispatch` node.
- If `state.needs_human_review == True` or `state.approval_status == "rejected"`, the conditional edge returns `END`, completely bypassing `email_node`.
- The user is alerted on the UI dashboard with an approval bar. The user can inspect the findings and click **Approve & Dispatch Email**, which hits `/api/run/{run_id}/approve` to trigger email dispatch, or **Reject**, which permanently cancels it.

---

### Q9: Why was SQLite selected over PostgreSQL, MongoDB, or a cloud database?
**Answer:**  
1. **Zero-Configuration Portability:** SQLite is an embedded, zero-dependency ACID-compliant SQL engine bundled standard with Python. It requires no external server process, daemon, credentials, or cloud network connectivity.
2. **Offline Jury Demonstration:** University juries often take place on evaluation laptops with restricted Wi-Fi. SQLite ensures 100% reliable local demonstration.
3. **Structured Relational Querying:** Schema migrations, foreign keys, and typed queries are cleanly managed via SQLAlchemy ORM, which can be swapped for PostgreSQL in production simply by altering the database URL.

---

### Q10: How does the application maintain 100% offline functionality?
**Answer:**  
1. **Local Data:** Sample expense records are stored in local CSV files (`backend/data/expenses.csv`).
2. **Local Database:** SQLite files (`expenses.db`, `expense_agent.db`) are created and managed on the local filesystem.
3. **Deterministic Categorization Fallback:** The categorization agent features a deterministic keyword/merchant lookup table that executes when external LLM API keys are absent.
4. **Development Email Simulation:** When `DEVELOPMENT_MODE=true`, the email service saves RFC 5322 email text files and copies the generated PDF attachment to `backend/reports/simulated_emails/`, simulating complete email dispatch without needing an active SMTP server.
