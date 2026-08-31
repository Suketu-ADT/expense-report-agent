# Expense Report Agent

A multi-agent AI system that autonomously generates travel expense reports from raw data.

## Architecture

This project is built using an Orchestrator + Specialist Agents architecture powered by LangGraph. All agents communicate through a shared state (`ExpenseReportState` blackboard), ensuring modularity and clear responsibility.

### 7 Agents:
1. **Orchestrator**: Parses the user request, resolves relative dates ("last month"), and constructs the execution plan.
2. **Data Retrieval**: Loads raw expense records (simulated from a CSV data source).
3. **Filter & Validation**: Filters records by date, validates missing amounts/dates, flags duplicates, and handles unsupported currencies. Flagged items require user review.
4. **Categorization**: Categorizes expenses into Airfare, Lodging, Meals, Ground Transport, or Other using deterministic rules, falling back to an LLM (Gemini 1.5) when uncertain.
5. **Calculation**: Deterministically aggregates totals into Confirmed and Provisional buckets, ensuring flagged amounts never modify confirmed totals silently.
6. **Report Generation**: Generates a professional PDF report containing an Executive Summary, Category Breakdown, Itemized Expenses, and a Needs Review section using ReportLab.
7. **Email Dispatch**: Emails the report via SMTP. Defaults to DEVELOPMENT_MODE (saving simulated emails locally to `backend/reports/simulated_emails`).

## Project Setup

### Environment Variables
Duplicate `backend/.env.example` as `backend/.env` and update values:
```env
GEMINI_API_KEY=your_gemini_api_key_here
FINANCE_EMAIL=finance@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM=reports@example.com
DEVELOPMENT_MODE=true
```

### Starting the Backend
Requires Python 3.12+ (or use `uv`).
```bash
cd backend
uv venv .venv
# Activate venv: .venv\Scripts\activate (Windows) or source .venv/bin/activate (Unix)
uv pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Starting the Frontend
Requires Node.js 18+.
```bash
cd frontend
npm install
npm run dev
```

### Running the Demo
1. Ensure both backend (`http://localhost:8000`) and frontend (`http://localhost:5173`) are running.
2. Open the frontend in your browser.
3. Click "Run Agent" to submit the demo request: "Generate my travel expense report for last month and email it to finance."
4. Observe the Agent Pipeline progress, review the generated report PDF in `backend/reports/`, and the simulated email in `backend/reports/simulated_emails/`.

### Automated Testing
To run the automated tests:
```bash
cd backend
$env:PYTHONPATH="."  # For Windows PowerShell
pytest tests/
```
