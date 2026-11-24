from app.services.evaluation_service import categorization_accuracy, review_and_retry_stats


def test_categorization_rule_tier_is_fully_accurate():
    """The keyword-rule half of the fixture never touches the LLM, so this
    must always be 100% regardless of whether GROQ_API_KEY is configured."""
    results = categorization_accuracy()
    assert results["rule"]["total"] > 0
    assert results["rule"]["accuracy"] == 1.0
    assert results["rule"]["mismatches"] == []


def test_categorization_fallback_tier_is_reported_not_asserted():
    """The LLM-fallback half depends on an optional API key; we only check
    that it runs and reports a number, without requiring any threshold."""
    results = categorization_accuracy()
    assert results["fallback"]["total"] > 0
    assert 0.0 <= results["fallback"]["accuracy"] <= 1.0


def test_review_agent_never_false_flags_a_clean_run():
    stats = review_and_retry_stats(trials=30, seed=1)
    assert stats["false_positive_rate"] == 0.0


def test_review_agent_always_catches_the_injected_discrepancy():
    stats = review_and_retry_stats(trials=30, seed=1)
    assert stats["true_positive_rate"] == 1.0


def test_correction_agent_always_resolves_in_one_retry():
    stats = review_and_retry_stats(trials=30, seed=1)
    assert stats["retry_resolution_rate"] == 1.0
