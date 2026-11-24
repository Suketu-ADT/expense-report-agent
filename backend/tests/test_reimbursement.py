import csv
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader
from fastapi.testclient import TestClient
from app.main import app, active_runs
from app.services.reimbursement import PolicyOptions, create_sheet, edit_item, ItemEdit, summary
from app.state.blackboard import ExpenseReportState, CategorizedExpense


def test_jury_review_and_persisted_dispatch(monkeypatch):
    monkeypatch.setenv("DEVELOPMENT_MODE", "true")
    client = TestClient(app)
    fixture = Path(__file__).resolve().parents[1] / "data" / "jury" / "claims.csv"
    monkeypatch.setattr("app.services.expense_service.EXPENSES_CSV", fixture)
    baseline_id = client.post("/api/run", json={"request_text": "July 2026"}).json()["run_id"]
    baseline = client.get(f"/api/run/{baseline_id}").json()
    assert baseline["totals"]["confirmed_total"] == 1550
    response = client.post("/api/run", json={"request_text": "July 2026", "policy": {"demo": True}})
    run_id = response.json()["run_id"]
    base = f"/api/run/{run_id}"
    report = client.get(base).json()
    assert report["raw_expenses"] == baseline["raw_expenses"]
    sheet = report["reimbursement"]
    assert (sheet["claimed"], sheet["approved"], sheet["held"]) == (155000, 80000, 1)
    assert client.post(base + "/approve").status_code == 409
    decision = {"revision": 0, "action": "accept", "note": "Taxi receipt confirms INR 300"}
    updated = client.post(base + "/claims/1", json=decision).json()
    assert (updated["approved"], updated["difference"], updated["held"]) == (110000, 45000, 0)
    assert client.post(base + "/claims/1", json=decision).status_code == 409
    active_runs.pop(run_id)
    pdf = PdfReader(BytesIO(client.get(base + "/reimbursement.pdf").content))
    report_text = "\n".join(page.extract_text() for page in pdf.pages)
    for detail in ("Approved (INR): 1100.00", "Difference (INR): 450.00", decision["note"]):
        assert detail in report_text
    assert client.get("/api/reports/" + report["report_id"]).json()["reimbursement"] == updated
    assert client.post(base + "/approve").json()["delivery_status"] == "delivered"
    assert client.post(base + "/approve").status_code == 409
    assert client.post(base + "/claims/1", json={**decision, "revision": 1}).status_code == 409


def test_attach_and_correct_receipt_keeps_original():
    claim = CategorizedExpense(id="C", merchant="Cafe", date="2026-07-10", amount=600, category="Meals", currency="INR")
    sheet = create_sheet(ExpenseReportState(user_id="test", categorized_expenses=[claim]), PolicyOptions())
    assert summary(sheet)["held"] == 1
    source = "Merchant: Cafe\nDate: 2026-07-11\nTotal: INR 600"
    edit_item(sheet, 0, ItemEdit(revision=0, action="attach", text=source))
    assert sheet["items"][0]["eligible"] is None
    edit_item(sheet, 0, ItemEdit(revision=1, action="correct", text=source.replace("-11", "-10"), note="Checked date"))
    assert summary(sheet)["approved"] == 60000
    assert sheet["items"][0]["source"] == source


def test_digital_receipt_pdf_and_ambiguous_total(monkeypatch):
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas
    from app.services.reimbursement import read_receipt
    fixture = BytesIO()
    pdf = Canvas(fixture)
    for index, line in enumerate(("City Taxi", "2026-07-10", "Grand Total INR 300.00")):
        pdf.drawString(40, 700 - index * 20, line)
    pdf.save()
    from app.agents import retrieval_agent
    from app.services.reimbursement import jury_claims
    monkeypatch.setattr(retrieval_agent, "get_expenses", lambda _: jury_claims())
    client = TestClient(app)
    run_id = client.post("/api/run", json={"request_text": "July 2026", "policy": {}}).json()["run_id"]
    url = f"/api/run/{run_id}/claims/1/receipt"
    result = client.post(url, params={"revision": 0}, files={"file": ("taxi.pdf", fixture.getvalue())})
    assert client.get(url).content == fixture.getvalue()
    assert result.status_code == 200
    text = result.json()["items"][1]["source"]
    assert read_receipt(text) == {"merchant": "City Taxi", "date": "2026-07-10", "amount": 30000}
    assert read_receipt(text + "\nTotal INR 310")["amount"] is None


def labelled_cases():
    fixture = Path(__file__).resolve().parents[1] / "data" / "jury" / "evaluation.csv"
    with fixture.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize("case", labelled_cases(), ids=lambda case: case["case"])
def test_labelled_reimbursement(case):
    claim = CategorizedExpense(id="E1", merchant="Sample Merchant", date="2026-07-10",
                               amount=case["claimed_inr"], category=case["category"], currency="INR")
    state = ExpenseReportState(user_id="evaluation", categorized_expenses=[claim])
    sheet = create_sheet(state, PolicyOptions())
    item = sheet["items"][0]
    if case["receipt_inr"]:
        receipt = f"Merchant: Sample Merchant\nDate: 2026-07-10\nTotal: INR {case['receipt_inr']}"
        edit_item(sheet, 0, ItemEdit(revision=0, action="attach", text=receipt))
    assert item["status"] == case["initial_status"]
    assert item["approved"] == int(case["initial_approved_paise"])
    if case["review_action"]:
        edit_item(sheet, 0, ItemEdit(revision=sheet["revision"], action=case["review_action"],
                                     note="Manually reviewed fixture"))
    assert item["status"] == case["final_status"]
    assert item["approved"] == int(case["final_approved_paise"])
