# Test Results

Generated 24 Nov 2026 against commit `d3bc8fc`. Reproduce with the commands
under each section.

## 1. Backend automated test suite — 88 / 88 passed

```powershell
cd backend
$env:PYTHONPATH="."; $env:DEVELOPMENT_MODE="true"
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

| Test file | Tests | Covers |
|---|---:|---|
| `test_pipeline.py` | 4 | Core pipeline: date resolution, validation, categorization, calculation |
| `test_regression_pipeline.py` | 8 | End-to-end graph regression across normal runs, discrepancy recovery, approval gating |
| `test_unit3_memory.py` | 6 | Persistent memory save/retrieve, cross-session durability, preferences |
| `test_unit4_collaboration.py` | 10 | Review/Correction collaboration, structured messaging, retry bounding, escalation |
| `test_api_extensions.py` | 5 | API layer: run endpoints, user preferences |
| `test_reimbursement.py` | 11 | Reimbursement policy engine, labelled case oracle (8 scenarios) |
| `test_receipt_agents.py` | 3 | Receipt upload, batch matching, duplicate/ambiguity detection |
| `test_receipt_debate.py` | 2 | Multi-agent debate guardrails (skips without a key / wrong candidate count) |
| `test_reflection.py` | 2 | Categorization reflection pass skip conditions |
| `test_planner.py` | 8 | Dynamic planner intent parsing, anomaly/comparison stages, injection resistance |
| `test_policy_rag.py` | 4 | Policy retrieval correctness and citation grounding |
| `test_guardrails.py` | 5 | Prompt-injection detection, sanitization, PII redaction, schema validation |
| `test_autonomy_levels.py` | 5 | Autonomy-level retry limits and warning-escalation behavior |
| `test_currency_tool.py` | 4 | Live/offline-fallback currency conversion |
| `test_evaluation.py` | 5 | Evaluation harness thresholds (categorization, Review Agent rates) |
| `test_report_cache.py` | 6 | Report cache correctness, copy semantics, bypass-write sync |
| **Total** | **88** | **All passing** |

## 2. Frontend build & lint — clean

```powershell
cd frontend
npm run build
npm run lint
```

- Build: succeeds, no errors (one informational bundle-size notice from Vite).
- Lint (`oxlint`): one pre-existing, unrelated warning in `ReportHistory.jsx` (an effect-timing style note); zero errors.

## 3. Large-dataset regression — 500 / 500 claims verified

```powershell
cd ExpenseFlow-Large-Dataset
..\expense-report-agent\backend\.venv\Scripts\python.exe run_test.py --backend ..\expense-report-agent\backend
```

```json
{
  "result": "passed",
  "assessed_claims": 500,
  "batches": 60,
  "batch_files": 474,
  "review_actions": 64,
  "agent_findings_confirmed": 64,
  "final_status_counts": { "eligible": 434, "rejected": 16, "accepted": 30 },
  "observed": {
    "source_rows": 500,
    "included_rows": 480,
    "duplicate_rows": 10,
    "outside_period_rows": 10,
    "claimed_paise": 94812138,
    "after_batch_approved_paise": 84989800,
    "after_batch_holds": 64,
    "final_approved_paise": 87305930,
    "final_difference_paise": 7506208,
    "final_holds": 0
  }
}
```

Every one of the 500 synthetic claims matched its hand-computed expected
status and approved amount at both checkpoints (after automated receipt
batching, and after simulated reviewer actions). This run exercises
duplicate detection, receipt reuse, ambiguous matches, amount mismatches,
conflicting totals, and missing evidence — the full edge-case catalogue the
dataset was built to cover.

## 4. Automated evaluation harness

```powershell
cd backend
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m app.services.evaluation_service
```

| Metric | Result |
|---|---|
| Categorization accuracy — rule tier (deterministic, asserted in CI) | **16 / 16 (100%)** |
| Categorization accuracy — LLM-fallback tier (reported, not asserted) | **10 / 10 (100%)**, with `GROQ_API_KEY` configured |
| Review Agent false-positive rate (30 seeded trials) | **0%** |
| Review Agent true-positive rate (30 seeded trials) | **100%** |
| Correction Agent retry-resolution rate | **100%** |

Full methodology and caveats: [`jury/evaluation_report.md`](../jury/evaluation_report.md).

## 5. Summary

| Layer | Result |
|---|---|
| Backend unit/integration tests | 88 / 88 passed |
| Frontend build | Clean |
| Frontend lint | Clean (1 pre-existing, unrelated warning) |
| Large-dataset regression (500 claims) | 500 / 500 passed |
| Evaluation harness (rule-tier, Review Agent) | 100% across all asserted metrics |
