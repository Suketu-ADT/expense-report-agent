# Expense Report Agent: Jury Demonstration Guide

This guide provides exact steps and Windows PowerShell commands to run, test, and demonstrate the Autonomous Expense Report Agent for the Unit III & IV Mini-Project Jury.

---

## 1. System Requirements & Environment

- **OS:** Windows 10/11
- **Python:** 3.11+ (Python 3.12 verified)
- **Node.js:** v18+ (v20+ recommended)
- **Database:** Local SQLite (`expenses.db` / `expense_agent.db`)
- **Network Requirement:** 100% offline capable (uses local SQLite, local mock CSV data, and simulated email dispatch).

---

## 2. Startup Instructions (PowerShell)

Open two PowerShell windows: one for the FastAPI backend and one for the React frontend.

### Terminal 1: Backend Setup & Launch
```powershell
# Navigate to backend directory
cd "c:\Users\Arpit singh\OneDrive\Desktop\Agentic AI\expense-report-agent\backend"

# (Optional) Activate existing virtual environment
.\.venv\Scripts\Activate.ps1

# Install / verify requirements if needed
pip install -r requirements.txt

# Start FastAPI server on port 8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Backend will be running at:* `http://localhost:8000` (API documentation at `http://localhost:8000/docs`)

---

### Terminal 2: Frontend Setup & Launch
```powershell
# Navigate to frontend directory
cd "c:\Users\Arpit singh\OneDrive\Desktop\Agentic AI\expense-report-agent\frontend"

# Start the Vite development server
npm run dev
```
*Frontend will be running at:* `http://localhost:5173`

---

## 3. Running Automated Tests

To execute the complete 25-test verification suite:
```powershell
cd "c:\Users\Arpit singh\OneDrive\Desktop\Agentic AI\expense-report-agent\backend"
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

**Expected Result:**
```
tests/test_api_extensions.py::test_api_health PASSED                     [  4%]
tests/test_api_extensions.py::test_api_report_history_empty_and_retrieval PASSED [  8%]
tests/test_api_extensions.py::test_api_saved_report_not_found PASSED     [ 12%]
tests/test_api_extensions.py::test_api_user_preferences_flow PASSED      [ 16%]
tests/test_api_extensions.py::test_api_approve_and_reject_flow PASSED    [ 20%]
tests/test_pipeline.py::test_resolve_last_month PASSED                   [ 24%]
tests/test_pipeline.py::test_validation_logic PASSED                     [ 28%]
tests/test_pipeline.py::test_categorization_logic PASSED                 [ 32%]
tests/test_pipeline.py::test_calculation_logic PASSED                    [ 36%]
tests/test_unit3_memory.py::test_1_save_and_retrieve_persistent_memory PASSED [ 40%]
tests/test_unit3_memory.py::test_2_persistence_across_new_database_session PASSED [ 44%]
tests/test_unit3_memory.py::test_3_historical_retrieval_when_no_records_exist PASSED [ 48%]
tests/test_unit3_memory.py::test_agent_message_audit_trail PASSED        [ 52%]
tests/test_unit3_memory.py::test_user_preferences_persistence PASSED     [ 56%]
tests/test_unit3_memory.py::test_memory_persistence_node_execution PASSED [ 60%]
tests/test_unit4_collaboration.py::test_4_expense_total_reconciliation PASSED [ 64%]
tests/test_unit4_collaboration.py::test_5_duplicate_transaction_handling PASSED [ 68%]
tests/test_unit4_collaboration.py::test_6_missing_field_review_behavior PASSED [ 72%]
tests/test_unit4_collaboration.py::test_7_structured_agent_communication PASSED [ 76%]
tests/test_unit4_collaboration.py::test_8_discrepancy_injection_and_detection PASSED [ 80%]
tests/test_unit4_collaboration.py::test_9_conditional_retry_and_recovery PASSED [ 84%]
tests/test_unit4_collaboration.py::test_10_maximum_retry_limit_and_escalation PASSED [ 88%]
tests/test_unit4_collaboration.py::test_11_escalation_when_correction_fails PASSED [ 92%]
tests/test_unit4_collaboration.py::test_12_and_13_prevention_of_dispatch_without_approval PASSED [ 96%]
tests/test_unit4_collaboration.py::test_14_prevention_of_duplicate_dispatch_during_retries PASSED [100%]

======================= 25 passed in 8.89s =======================
```

---

## 4. Live Jury Demonstration Scenarios

### Scenario A: Baseline Normal Run & Memory Persistence (Unit III)

1. Open `http://localhost:5173` in your browser.
2. In the prompt input, enter:
   `Generate my travel expense report for June 2026 and email it to finance.`
3. Ensure the **"Unit IV Demo: Inject calculation discrepancy"** checkbox is **unchecked**.
4. Click **Run Agent**.
5. **Observe in Real-Time:**
   - **Agent Pipeline:** Cards transition dynamically through:
     *Orchestrator → Data Retrieval → Filter & Validation → Categorization → Calculation → Expense Review → Report Generation → Memory Persistence → Email Dispatch*.
   - **Unit III Memory Recall Banner:** Displays whether previous reports were found in SQLite.
   - **Summary Cards:** Shows Confirmed Total (`₹65,650.00`), Flagged Expenses, and Categories.
   - **Expense Table:** Lists all 20 transactions categorized into Airfare, Lodging, Meals, and Ground Transport.
   - **Expense Review Panel:** Shows `REVIEW PASSED` (0 findings).
   - **Report History (Bottom of page):** The newly generated report immediately appears with its unique `RPT-XXXXXXXX` ID, total, and expandable category breakdown.
6. **Demonstrate Persistence:**
   - Refresh the browser (`F5`).
   - The Report History panel still displays all previously generated reports retrieved directly from SQLite.

---

### Scenario B: Controlled Failure & Multi-Agent Self-Healing Recovery (Unit IV)

1. Check the box: **"Unit IV Demo: Inject calculation discrepancy"**.
2. Click **Run Agent**.
3. **What happens under the hood:**
   - An intentional arithmetic discrepancy (+₹500 phantom amount) is simulated in the reported calculation total.
   - The **Expense Review Agent** runs its independent Python verification and detects the mismatch:
     `Confirmed total mismatch: calculated ₹65650.00 vs reported ₹66150.00`.
   - The Review Agent marks status as `NEEDS CORRECTION` and transmits a structured `AgentMessage` to the **Correction Agent**.
   - The LangGraph conditional edge routes execution to `Correction`.
   - The Correction Agent recalculates confirmed totals from raw records, logs the fix, and emits a `correction_result` message.
   - LangGraph routes to `Re-Review` (pass 2).
   - The Review Agent re-audits the state: now clean, overall status becomes `PASSED`.
   - The pipeline continues to PDF generation, Memory Persistence, and Email Dispatch.
4. **Observe on the Screen:**
   - In the **Expense Review Panel**, view the audit trace:
     - Badge displays `REVIEW PASSED · 1 finding(s) · 1 retry(ies)`.
     - Review findings show the total mismatch marked with a green `[RESOLVED]` badge.
     - Under **Agent Communication**, observe the structured messages exchanged between `Expense Review` and `Correction`.

---

### Scenario C: Human-in-the-Loop Approval & Email Gate

1. If an expense report has unresolvable critical flags or exceeds retry limits, the system sets `needs_human_review = True`.
2. Notice that the completion banner displays:
   `Email dispatch held: Requires human review before sending.`
3. The **HUMAN APPROVAL GATE** bar provides two action buttons:
   - **Approve & Dispatch Email:** Reviewer accepts the findings and triggers immediate delivery.
   - **Reject:** Reviewer rejects the submission, permanently halting email dispatch.
4. Click **Approve & Dispatch Email**:
   - The button transitions to `Approved & Dispatched`.
   - Delivery status updates in both the live state and the persistent SQLite database.

---

## 5. Troubleshooting & FAQ

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `Failed to fetch / Connection refused` | Backend server not running | Ensure `python -m uvicorn app.main:app` is running on port 8000. |
| `Zero expenses found` | CSV file missing from `data/` | Click **Upload CSV** and select `backend/data/expenses.csv` or sample file. |
| `Vite port conflict` | Port 5173 occupied | Vite will automatically switch to 5174; update browser address bar accordingly. |
| `Simulated email location` | `DEVELOPMENT_MODE=true` | Generated emails are saved as `.txt` files in `backend/reports/simulated_emails/`. |

---

## 6. Offline Limitations Disclosure

- **LLM Categorization Fallback:** In offline mode without an active Gemini API key, the categorization agent uses its deterministic keyword/merchant dictionary fallback (`IndiGo` → Airfare, `Taj` → Lodging, `Starbucks` → Meals, `Uber` → Ground Transport). This ensures 100% offline demonstration reliability without cloud API failures.
- **Email Delivery:** In development mode (`DEVELOPMENT_MODE=true` in `.env`), email dispatch writes text transcripts and PDF copies to `backend/reports/simulated_emails/`, eliminating the requirement for live SMTP servers.
