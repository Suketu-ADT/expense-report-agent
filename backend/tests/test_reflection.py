from app.services.llm_service import categorize_with_reflection, reflect_on_category


def test_reflection_skipped_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    category, critique, revised = categorize_with_reflection("Mystery Merchant", 100.0, "")
    assert category == "Other / Uncategorized"
    assert critique is None
    assert revised is False


def test_reflection_skipped_when_first_pass_is_already_uncategorized(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test_key")
    category, critique, revised = reflect_on_category("Mystery Merchant", 100.0, "", "Other / Uncategorized")
    assert category == "Other / Uncategorized"
    assert critique is None
    assert revised is False
