from app.services.llm_service import debate_receipt_match


def test_debate_skipped_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    winner, transcript = debate_receipt_match(
        "Lunch Cafe", "2026-07-10", 4.50,
        [("cafe-a.txt", "Merchant: Lunch Cafe\nDate: 2026-07-10\nTotal: INR 450"),
         ("cafe-b.txt", "Merchant: Lunch Cafe\nDate: 2026-07-10\nTotal: INR 400")],
    )
    assert winner is None
    assert transcript == []


def test_debate_skipped_when_not_exactly_two_candidates(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test_key")
    winner, transcript = debate_receipt_match("Lunch Cafe", "2026-07-10", 4.50, [("only.txt", "text")])
    assert winner is None
    assert transcript == []
