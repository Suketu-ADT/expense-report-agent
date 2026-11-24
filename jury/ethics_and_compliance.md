# Ethics & Compliance Notes

Short, honest notes on where this system touches money, personal data and
automated decisions — written for a jury asking "should this be trusted",
not to claim the system is risk-free.

## 1. Bias in automated reimbursement decisions

The reimbursement engine's rules are uniform and category-based (a Meals
cap, receipt-matching requirements), not learned from historical approval
patterns — so there is no risk of it absorbing and repeating *past* biased
approvals the way a model trained on historical decisions could. The
remaining bias risk is narrower and real: the categorization LLM fallback
(`app/services/llm_service.py`) could, in principle, categorize
semantically similar merchants differently depending on phrasing or
language the keyword rules don't anticipate — e.g. a regional restaurant
name it doesn't recognize as "Meals." This is a fairness concern (not every
employee's spending is parsed with equal confidence), not a financial
safety one, since category only affects the Meals cap; every category's
receipt-matching and reimbursement amount check is identical. Mitigation in
place: the deterministic keyword rules run first and cover the common
cases without touching the LLM at all; the fallback only activates for
merchants the rules can't classify, output is whitelist-validated (never
free text), and a human reviewer sees — and can correct — every held or
ambiguous claim before anything is paid.

## 2. Financial-data privacy

Expense records (merchant names, amounts, dates) and uploaded receipts are
processed and stored entirely locally — SQLite on disk, no third-party
analytics, no telemetry. The two points where data leaves the machine by
design are: (a) the optional Groq LLM call for categorization fallback,
which sends only a merchant name, amount and hint — never a full receipt,
a report total, or an employee identity — and (b) email dispatch of the
final report, which is simulated in development mode and goes only to the
configured `FINANCE_EMAIL` in production mode. Receipts can contain
incidental personal data (a name on a hotel folio, a card's last four
digits in OCR'd text); these are stored for the reviewer's own use in
approving the claim and are not exposed anywhere outside this application's
own authenticated views. See `jury/extended_problem_statement.md`'s
guardrails section for the prompt-injection and PII-redaction measures
applied to any text that reaches an LLM or an audit log.

## 3. Why human sign-off is mandated, not optional

Every report — regardless of how clean the Review Agent's checks come back
— stops at an explicit approval gate before email dispatch
(`check_after_persist` in `app/graph/expense_graph.py`). This is a
deliberate design constraint, not a missing feature: an agent that can
independently verify its own arithmetic is still an agent whose arithmetic
could be wrong in a way its own checks don't anticipate (a category it
miscounted, a policy clause it mis-cited). For money leaving the
organization, the cost of a wrongly-withheld report (a delay) is far lower
than the cost of a wrongly-sent one (an unauthorized payment), so the
system is built to fail toward "ask a human" rather than "proceed anyway."
This is the same principle behind the bounded retry loop (3 attempts, then
escalate rather than keep guessing) and the receipt-matching agents'
behavior on ambiguity (route to a reviewer rather than pick the more likely
receipt).

## 4. What this system does not claim

- It does not claim its categorization or reimbursement decisions are
  bias-free in every edge case — only that the cases it is least confident
  about are the ones a human sees before money moves.
- It does not claim to be a compliance system for any specific regulatory
  framework (SOX, GDPR, DPDP Act, etc.) — it is a student mini/sem-end
  project demonstrating the *patterns* (audit trails, human-in-the-loop,
  data minimization in LLM calls) that a production compliance system
  would need to build on, not a certified implementation of one.
- It does not claim the evaluation numbers in `jury/evaluation_report.md`
  generalize beyond the labelled fixtures and datasets they were measured
  on — see that document's own "what this does and doesn't claim" section.
