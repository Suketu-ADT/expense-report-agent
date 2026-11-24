# Demo Video — Shot-by-Shot Script

Target length: ~6–7 minutes. Record at 1440×900 or larger, screen only (no
webcam needed) with your own narration audio. Start both servers first:

```powershell
# Terminal 1
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload

# Terminal 2
cd frontend
npm run dev
```

Open `http://localhost:5173` before you hit record. Pause between shots if
you're recording in one take — it's easier to re-record one shot than the
whole thing.

---

## Shot 1 — Cold open (0:00–0:30)

**Screen:** The empty Overview page, nothing run yet.

**Say:**
> "This is ExpenseFlow AI — an autonomous, multi-agent system that turns a raw expense spreadsheet into a validated, reviewed report, with a human approving before anything goes out. It started as a Unit III and Unit IV mini-project — memory and multi-agent review — and for this sem-end submission we extended it with dynamic planning, tool use, safety guardrails, and an automated evaluation harness. I'll walk through the live system, then show the numbers behind it."

**Do:** Nothing yet — just let this sentence play over the empty dashboard.

---

## Shot 2 — Dynamic planning in action (0:30–1:45)

**Screen:** Overview page, Request box.

**Do:**
1. Click the Request textarea, select all, type:
   `Generate my travel expense report for July 2026, flag anything over 2000, and compare it to last month.`
2. Click **Generate report**. Wait ~3 seconds.
3. Scroll down to the summary cards.

**Say:**
> "Notice I asked it to flag anomalies and compare to last month, in plain English. Watch the summary — it generated two extra cards it wouldn't show for a plain request: Flagged anomalies, and a comparison against June 2026. That's a Planner parsing the request and deciding which optional pipeline stages actually apply — not a fixed sequence that ignores what I asked for."

**Screen:** Point at (or zoom into) the "Flagged anomalies: 108" and "vs June 2026: +₹9,42,121.38" cards.

---

## Shot 3 — The agent pipeline (1:45–3:00)

**Do:**
1. Click **Agent pipeline** in the sidebar.
2. Let the 13-stage grid show fully.
3. Click the **Anomaly Detection** stage, then **Period Comparison**, to expand their log entries.
4. Scroll to the **Agent run log** below and point out the Orchestrator's planning line (`Plan (llm): anomaly_threshold=2000.0, compare_to_previous=True`).

**Say:**
> "Thirteen stages, each reporting its own status live. Anomaly Detection and Period Comparison both completed because I asked for them — on a plain request, they'd show 'Skipped,' never silently doing nothing. The run log shows exactly what the planner parsed out of my request, so this is fully auditable, not a black box."

---

## Shot 4 — Memory and the report cache (3:00–3:45)

**Do:**
1. Click **Report memory** in the sidebar.
2. Scroll through the list of recalled prior reports for July 2026.
3. Click **Report history** — point out reports from earlier sessions still present.

**Say:**
> "This is long-term memory — every report persists in SQLite across restarts, and the Orchestrator proactively recalls prior reports for the requested period at the start of every run. We also added a write-through cache in front of this database, since report history is read far more often than it's written — verified to never go stale, including after we found and fixed two places that updated a report directly and bypassed it."

---

## Shot 5 — Policy-grounded RAG (3:45–4:45)

**Do:**
1. Go back to **Overview**, click **Two-claim jury demo** under "Try a sample."
2. Click **Review claim decisions** once it finishes.
3. Point at the **Campus Cafe** claim's reason line.

**Say:**
> "This is retrieval-augmented grounding. Instead of a hardcoded string, the reimbursement engine retrieves the actual policy clause from a travel-policy document and cites it — 'Travel Policy, Section 2.1, Meals, capped at INR 800 per claim.' It's a local retriever, no embeddings or network call needed, so it still works fully offline. And it only grounds the explanation — the approved amount comes from the same deterministic arithmetic as before, verified against a 500-claim regression test."

---

## Shot 6 — Multi-agent collaboration on receipts (4:45–5:45)

**Do:**
1. Back on Overview, click **Receipt agent demo**.
2. Click **Review claim decisions**, then **Match sample receipts**.
3. Expand **Last receipt batch** and point at the Resolution agent / Evidence reviewer lines for both claims.

**Say:**
> "Here, two specialist agents collaborate on receipt matching: the Exception Resolution Agent searches the batch for a matching receipt, and the Evidence Reviewer independently verifies merchant, date, amount and policy compliance before anything is approved. The ambiguous case — a taxi fare that doesn't quite match — is routed to a human reviewer instead of guessed."

---

## Shot 7 — The human approval gate (5:45–6:15)

**Do:**
1. Click **Review & approvals**.
2. Point at the **Approve and send** / **Reject** buttons without clicking (so the video doesn't show a real/simulated dispatch unless you want it to — optional to actually click Approve here).

**Say:**
> "No matter how clean the review comes back, nothing is emailed until a human explicitly approves it here. That's true in every one of the three configurable autonomy levels we added — cautious, co-pilot and trusting only change how much auto-correction is trusted before escalating; this gate itself is never configurable."

---

## Shot 8 — The numbers (6:15–7:00)

**Screen:** Either screen-record yourself opening `docs/TEST_RESULTS.md` / `jury/evaluation_report.md`, or show a terminal running:

```powershell
cd backend
$env:PYTHONPATH="."; $env:DEVELOPMENT_MODE="true"
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

**Say:**
> "All of this is backed by numbers, not just a demo: 88 automated tests passing, a 500-claim synthetic dataset where every single claim matched its hand-computed expected outcome, and an evaluation harness scoring categorization accuracy and review-agent detection rates — all at or near 100 percent. Full methodology is in the submitted report. Thank you."

**End card (optional):** A title slide with the repo link — reuse the Thank You slide from the presentation deck, screen-recorded for 3 seconds.

---

## Notes for recording

- If `GROQ_API_KEY` isn't configured in your `backend/.env`, Shots 2 and 5 still work (the planner and categorization fall back to deterministic behavior) but the exact log text will say `Plan (deterministic): ...` instead of `Plan (llm): ...` — adjust the narration line in Shot 3 accordingly.
- Re-record a shot rather than the whole video if something glitches — each shot is self-contained (reload `http://localhost:5173` between shots if state gets confusing).
- Keep each spoken line under ~20 seconds; pause on screen slightly longer than you think you need to, so a viewer has time to actually read what's on screen.
