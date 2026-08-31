# Expense Report Agent

A multi-agent AI system built with LangGraph, FastAPI, and React that autonomously retrieves, validates, calculates, generates, and emails travel expense reports.

## Architecture

This project is built using an Orchestrator + Specialist Agents architecture powered by LangGraph. All agents communicate through a shared state (`ExpenseReportState` blackboard), ensuring modularity and clear responsibility.

### 7 Agents:
1. **Orchestrator**: Parses the user request, resolves relative dates ("last month"), and constructs the execution plan.
2. **Data Retrieval**: Loads raw expense records from the backend. (Supports dynamic CSV uploads from the UI).
3. **Filter & Validation**: Filters records by date, validates missing amounts/dates, flags duplicates, and handles unsupported currencies. Flagged items require user review.
4. **Categorization**: Categorizes expenses into Airfare, Lodging, Meals, Ground Transport, or Other using deterministic rules, falling back to an LLM (powered by **Groq / Llama3**) when uncertain.
5. **Calculation**: Deterministically aggregates totals into Confirmed and Provisional buckets, ensuring flagged amounts never modify confirmed totals silently.
6. **Report Generation**: Generates a professional PDF report containing an Executive Summary, Category Breakdown, Itemized Expenses, and a Needs Review section using ReportLab.
7. **Email Dispatch**: Emails the report via SMTP. Defaults to DEVELOPMENT_MODE (saving simulated emails locally to `backend/reports/simulated_emails`).

## Project Setup

### Environment Variables
Duplicate `backend/.env.example` as `backend/.env` and update values:
```env
GROQ_API_KEY=your_groq_api_key_here
FINANCE_EMAIL=finance@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_gmail_address
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM=your_gmail_address
DEVELOPMENT_MODE=true # Change to false to send real emails
```

### Starting the Backend
Requires Python 3.12+.
```bash
cd backend
python -m venv .venv
# Activate venv: .venv\Scripts\activate (Windows) or source .venv/bin/activate (Unix)
pip install -r requirements.txt
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
3. Use the **Upload CSV** button to supply your own financial data (optional).
4. Click **Run Agent** to submit the request: "Generate my travel expense report for last month and email it to finance."
5. Observe the Agent Pipeline progress, review the generated report PDF in `backend/reports/`, and the simulated/real email in your inbox.

### Automated Testing
To run the automated tests:
```bash
cd backend
$env:PYTHONPATH="."  # For Windows PowerShell
pytest tests/
```
