# Model Files — Note

This project does not train or ship a custom machine-learning model, so
there are no local weight files, checkpoints, or model artefacts to
include in this submission. This is a deliberate design choice, not a gap:

- The only model involved is a **third-party, API-hosted LLM** (Groq,
  `openai/gpt-oss-20b`), used for exactly three optional, **non-financial**
  decisions:
  1. The categorization fallback (when keyword rules don't match a merchant).
  2. A reflection/self-critique pass over that fallback's proposal.
  3. The Planner's optional refinement of a request's parsed intent.
- **All financial arithmetic and the independent Review Agent are
  deliberately LLM-free** — deterministic Python only, for auditability
  and reproducibility (see `jury/extended_problem_statement.md` §5.1).
- **Every one of the three LLM call sites has a fully deterministic,
  offline-safe fallback.** Remove `GROQ_API_KEY` from `backend/.env` and
  the system keeps working identically, just without the optional
  refinement — verified by the test suite, which runs both with and
  without a key configured.

## What stands in for a model here

| Instead of... | This project uses... |
|---|---|
| Trained classifier weights | Deterministic keyword rule tables in `backend/app/agents/categorization_agent.py` and `validation_agent.py` |
| A fine-tuned policy model | A retrieval-grounded policy document, `backend/data/policy/travel_policy.md`, queried by `backend/app/services/policy_rag.py` |
| Model configuration / hyperparameters | `backend/requirements.txt`, `backend/.env.example` (the optional `GROQ_API_KEY`) |
| A training dataset | The *evaluation* fixtures in `backend/data/evaluation/categorization_labels.csv` and the jury dataset `ExpenseFlow-Large-Dataset/` — used to score the system, not to train anything |

Full detail: `docs/submission/ExpenseFlow_AI_Full_Technical_Report.docx`,
Section 13 (Model Files — Note).
