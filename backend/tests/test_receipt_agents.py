from datetime import date
from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import active_runs, app
from app.services.receipt_upload import read_photo
from app.state.blackboard import Expense


def test_resolution_demo_resolves_metro_and_escalates_taxi():
    client = TestClient(app)
    run_id = client.post("/api/run", json={
        "request_text": "July 2026", "policy": {"resolution_demo": True},
    }).json()["run_id"]
    url = f"/api/run/{run_id}"
    report = client.get(url).json()
    before = report["reimbursement"]
    assert (before["claimed"], before["approved"], before["held"]) == (180000, 80000, 2)

    params = {"revision": before["revision"], "demo": True}
    response = client.post(url + "/receipt-review", params=params)
    assert response.status_code == 200, response.text
    reviewed = response.json()
    assert (reviewed["approved"], reviewed["held"]) == (105000, 1)
    outcomes = {row["claim_id"]: row["outcome"] for row in reviewed["receipt_review"]["claims"]}
    assert outcomes == {"TAXI-02": "escalated", "METRO-03": "resolved"}
    assert b"CM-119" in client.get(url + "/claims/2/receipt").content
    assert client.post(url + "/receipt-review", params=params).status_code == 409
    assert client.post(url + "/approve").status_code == 409

    response = client.post(url + "/claims/1", json={
        "revision": reviewed["revision"], "action": "accept", "note": "Taxi receipt confirms INR 300.",
    })
    assert response.status_code == 200, response.text
    final = response.json()
    assert (final["approved"], final["held"], final["difference"]) == (135000, 0, 45000)
    active_runs.pop(run_id)
    assert client.get(f"/api/reports/{report['report_id']}").json()["reimbursement"] == final
    pages = PdfReader(BytesIO(client.get(url + "/reimbursement.pdf").content)).pages
    report_text = "\n".join(page.extract_text() for page in pages)
    assert "Receipt and payable amount verified against the policy." in report_text
    assert "Taxi receipt confirms INR 300." in report_text


def test_uploaded_batch_flags_reuse_ambiguity_and_unreadable_total(monkeypatch):
    from app.agents import retrieval_agent

    claims = [
        ("R1", "City Taxi", 300), ("R2", "City Taxi", 350),
        ("R3", "Lunch Cafe", 450), ("R4", "Central Metro", 250),
    ]
    monkeypatch.setattr(retrieval_agent, "get_expenses", lambda _: [
        Expense(id=claim_id, merchant=merchant, amount=amount, date=date(2026, 7, 10), currency="INR")
        for claim_id, merchant, amount in claims
    ])
    client = TestClient(app)
    run_id = client.post("/api/run", json={"request_text": "July 2026", "policy": {}}).json()["run_id"]
    url = f"/api/run/{run_id}"

    taxi = "Receipt ID: TAXI5\nMerchant: City Taxi\nDate: 2026-07-10\nTotal: INR "
    response = client.post(url + "/claims/0", json={"revision": 0, "action": "attach", "text": taxi + "300"})
    assert response.status_code == 200, response.text
    cafe = "Merchant: Lunch Cafe\nDate: 2026-07-10\nTotal: INR "
    metro = "Merchant: Central Metro\nDate: 2026-07-10\nTotal: INR 250\nTotal: INR 252"
    batch = {
        "taxi-copy.txt": taxi + "350", "cafe-a.txt": cafe + "450", "cafe-b.txt": cafe + "400",
        "metro.txt": metro,
    }
    response = client.post(url + "/receipt-review", params={"revision": 1}, files=[
        ("files", (name, source.encode())) for name, source in batch.items()
    ] + [("files", ("bad.txt", b"\xff"))])
    assert response.status_code == 200, response.text
    reviewed = response.json()
    reasons = {row["claim_id"]: row["verification"] for row in reviewed["receipt_review"]["claims"]}
    assert "already supports another claim" in reasons["R2"]
    assert "Multiple receipts or claims" in reasons["R3"]
    assert "unreadable or ambiguous" in reasons["R4"]
    assert (reviewed["held"], reviewed["approved"]) == (3, 30000)
    assert reviewed["items"][3]["eligible"] is None
    assert client.get(url + "/claims/3/receipt").content == metro.encode()
    assert any(file["name"] == "bad.txt" for file in reviewed["receipt_review"]["files"])
    receipt_reuse = client.post(url + "/claims/1", json={
        "revision": reviewed["revision"], "action": "attach", "text": taxi + "350",
    })
    assert receipt_reuse.status_code == 422


def test_photo_retry_recovers_missing_fields_and_preserves_conflicting_amounts(monkeypatch):
    base = "Merchant: City Taxi\nDate: 2026-07-10"
    full = base + "\nTotal: INR 350"
    calls = []

    def extract(content, *, psm=None):
        calls.append(psm)
        return full if psm else content.decode()

    monkeypatch.setattr("app.services.receipt_upload.receipt_text", extract)
    text, action = read_photo(base.encode(), retry=True)
    assert (text, calls) == (full, [None, 11])
    assert "recovered" in action

    ambiguous = full + "\nTotal: INR 300"
    calls.clear()
    assert read_photo(ambiguous.encode(), retry=True)[0] == ambiguous
    assert calls == [None]
