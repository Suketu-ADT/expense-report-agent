"""
Evaluation harness: scores the agent pipeline against labelled data and
synthetic trials instead of relying on live demos alone.

Three independent measurements:
1. Categorization accuracy — against a hand-labelled fixture
   (`data/evaluation/categorization_labels.csv`), split into "rule" rows
   (covered by the deterministic keyword rules, so this half is always
   100% and safe to assert on in CI) and "fallback" rows (require the LLM
   fallback; reported but not asserted on, since it depends on an optional
   API key).
2. Review Agent detection rates — over N synthetic trials with randomized
   expense data, how often the Review Agent correctly flags an injected
   arithmetic discrepancy (true positive rate) and how often it wrongly
   flags a clean run (false positive rate).
3. Retry-loop resolution rate — of the trials the Review Agent correctly
   flagged, how many the Correction Agent resolves to "passed" in one pass.

This only reads labelled fixtures and runs agents in-process; it makes no
network calls and needs no API key to produce its primary, asserted numbers.
"""
import csv
import random
from datetime import date
from pathlib import Path
from typing import Any, Dict

from app.agents.calculation_agent import calculation_node
from app.agents.categorization_agent import categorization_node
from app.agents.correction_agent import correction_node
from app.agents.review_agent import review_node
from app.state.blackboard import CategorizedExpense, Expense, ExpenseReportState

CATEGORIZATION_LABELS = (
    Path(__file__).resolve().parents[2] / "data" / "evaluation" / "categorization_labels.csv"
)


def categorization_accuracy() -> Dict[str, Any]:
    with CATEGORIZATION_LABELS.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    expenses = [
        Expense(id=f"EVAL-{i}", date=date(2026, 7, 1), merchant=row["merchant"],
                amount=float(row["amount"]), currency="INR", category_hint=row["hint"] or None)
        for i, row in enumerate(rows)
    ]
    state = ExpenseReportState(user_id="evaluation", filtered_expenses=expenses)
    state = categorization_node(state)
    predicted = {e.id: e.category for e in state.categorized_expenses}

    results = {"rule": {"correct": 0, "total": 0, "mismatches": []},
               "fallback": {"correct": 0, "total": 0, "mismatches": []}}
    for i, row in enumerate(rows):
        bucket = results[row["tier"]]
        bucket["total"] += 1
        actual = predicted[f"EVAL-{i}"]
        if actual == row["expected_category"]:
            bucket["correct"] += 1
        else:
            bucket["mismatches"].append(
                {"merchant": row["merchant"], "expected": row["expected_category"], "actual": actual}
            )

    for bucket in results.values():
        bucket["accuracy"] = bucket["correct"] / bucket["total"] if bucket["total"] else None
    return results


def _random_trial_state(rng: random.Random, inject: bool) -> ExpenseReportState:
    categories = ["Airfare", "Lodging", "Meals", "Ground Transport"]
    n = rng.randint(2, 6)
    expenses = [
        CategorizedExpense(
            id=f"T{i}", date=date(2026, 7, 1), merchant=f"Merchant {i}",
            amount=round(rng.uniform(100, 5000), 2), currency="INR",
            category=rng.choice(categories),
        )
        for i in range(n)
    ]
    state = ExpenseReportState(user_id="evaluation", categorized_expenses=expenses, inject_discrepancy=inject)
    return calculation_node(state)


def review_and_retry_stats(trials: int = 30, seed: int = 42) -> Dict[str, Any]:
    rng = random.Random(seed)
    false_positives = 0
    true_positives = 0
    resolved = 0

    for _ in range(trials):
        clean = review_node(_random_trial_state(rng, inject=False))
        if clean.review_result.overall_status != "passed":
            false_positives += 1

        corrupted = review_node(_random_trial_state(rng, inject=True))
        if corrupted.review_result.overall_status == "needs_correction":
            true_positives += 1
            corrected = review_node(correction_node(corrupted))
            if corrected.review_result.overall_status == "passed":
                resolved += 1

    return {
        "trials": trials,
        "false_positive_rate": false_positives / trials,
        "true_positive_rate": true_positives / trials,
        "retry_resolution_rate": resolved / true_positives if true_positives else None,
    }


def build_report() -> Dict[str, Any]:
    return {
        "categorization": categorization_accuracy(),
        "review_agent": review_and_retry_stats(),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_report(), indent=2))
