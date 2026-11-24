# Agent Taxonomy

Each agent in the pipeline classified against the standard agent types
(Russell & Norvig, *Artificial Intelligence: A Modern Approach*), with the
file and the specific mechanism that earns the classification.

| Agent | File | Type | Why |
|---|---|---|---|
| **Orchestrator** | `app/agents/orchestrator.py` | **Goal-based** | Does not just react to the current input — it maintains a goal (produce the requested report for the resolved period), consults memory to check whether that goal is already satisfied (`get_reports_by_period`), and plans the actions needed to reach it (`execution_plan`) before any work happens. |
| **Planner (inside Orchestrator)** | `app/services/planner_service.py` | **Goal-based**, with **model-based** perception | Forms an internal model of what the user is asking for (`RequestIntent`) from an unstructured string, then uses that model — not the raw string — to decide which stages belong in the plan. The deterministic regex pass is the "model" of what the request means; the optional LLM pass refines that model, never replaces the goal-directed planning step itself. |
| **Filter & Validation** | `app/agents/validation_agent.py` | **Simple reflex** | Applies fixed condition-action rules per record (missing date → flag, duplicate fingerprint → exclude, unsupported currency → flag) with no memory of past runs and no lookahead — each expense is judged in isolation against a fixed rule set. |
| **Categorization** | `app/agents/categorization_agent.py` | **Simple reflex**, falling back to **model-based** | The keyword path is a pure condition-action table (merchant contains "uber" → Ground Transport). When no rule fires, it falls back to a model-based step: the LLM forms an internal judgment about what kind of merchant this is from context (merchant name, amount, hint) that the fixed rule table can't capture directly. |
| **Calculation** | `app/agents/calculation_agent.py` | **Simple reflex** | Deterministic arithmetic over the current state only — no model of the world beyond the numbers in front of it, no goal beyond "sum correctly." |
| **Anomaly Detection** | `app/agents/anomaly_agent.py` | **Simple reflex** | One condition-action rule (amount > threshold → flag), parameterized by the Planner's output but otherwise stateless per expense. |
| **Period Comparison** | `app/agents/comparison_agent.py` | **Model-based** | Explicitly builds a model of "what happened last period" by querying persistent memory, then compares the current world state against that model to produce a delta — it cannot do its job from the current state alone. |
| **Expense Review** | `app/agents/review_agent.py` | **Utility-based** | Doesn't just detect *a* problem — it independently recomputes the correct values and weighs multiple possible findings by severity (`critical` vs `warning`) to decide the overall outcome (`passed` / `needs_correction` / escalate), which is a utility judgment over several possible states, not a single fixed rule. |
| **Correction** | `app/agents/correction_agent.py` | **Utility-based** | Chooses between several possible remedies per finding type (recalculate totals, strip a duplicate, flag a field, escalate) based on which action actually resolves the specific finding — and separately weighs "can I fix this" vs. "this needs a human" (`report_inconsistency` → escalate rather than guess). |
| **Report Generation / Email Dispatch** | `app/agents/report_agent.py`, `app/agents/email_agent.py` | **Simple reflex** | Fixed transformation of state into an artifact (PDF) or action (send), gated by conditions set upstream rather than by their own reasoning. |
| **Exception Resolution** | `app/agents/exception_resolution_agent.py` | **Model-based** | Builds a model of which uploaded receipts could plausibly belong to which held claims (by merchant+date fingerprint) before acting, and explicitly represents uncertainty (ambiguous matches are routed to a human rather than guessed). |
| **Evidence Reviewer** | `app/agents/evidence_review_agent.py` | **Utility-based** | Weighs multiple independent checks (merchant match, date validity, amount match, policy cap) to decide whether a receipt fully clears a claim, partially clears it pending a human, or doesn't clear it at all — not a single pass/fail rule. |

## Why this matters beyond the label

The taxonomy isn't decorative: it maps directly onto *why* each agent is
built the way it is.

- Every **simple reflex** agent (Validation, Calculation, Anomaly Detection,
  Report/Email) is also the set that stays 100% deterministic and LLM-free
  — reflex agents are exactly the ones where non-determinism would be
  unacceptable (financial arithmetic, policy thresholds).
- Every **model-based** agent (Period Comparison, Exception Resolution,
  the Categorization fallback) is the set that reads from memory or forms
  a judgment under uncertainty — and in every case, uncertainty is
  surfaced rather than silently resolved (an unmatched receipt goes to a
  human, not to a guess).
- Every **utility-based** agent (Review, Correction, Evidence Reviewer) is
  the set that has to choose among several possible actions or outcomes —
  and in every case, the "utility function" is written down as explicit,
  auditable logic (severity levels, finding types, retry limits), not
  learned or implicit.
- The **Orchestrator** is the only **goal-based** agent, which matches its
  role: it's the one component whose job is to decide what the rest of the
  system is for on this particular run.

No agent here is a **learning agent** — nothing in the pipeline updates its
own behavior from past runs' outcomes (memory recall informs *context*, not
*parameters*). That is a deliberate scope boundary for a financial pipeline:
an agent that reconciles money should not quietly change how it reconciles
money based on inferred patterns.
