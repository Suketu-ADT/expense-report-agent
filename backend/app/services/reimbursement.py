"""Receipt evidence and INR reimbursement policy. Amounts are stored in paise."""
from pathlib import Path
from decimal import Decimal, InvalidOperation
import re
from typing import Literal
from pydantic import BaseModel, Field

from app.services.expense_service import read_expenses_csv
from app.services.policy_rag import retrieve_clause


class PolicyOptions(BaseModel):
    meal_cap: int = Field(default=800, gt=0, le=1000000)
    demo: bool = False
    resolution_demo: bool = False


class ItemEdit(BaseModel):
    revision: int = Field(ge=0)
    action: Literal["attach", "correct", "accept", "reject"]
    text: str = Field(default="", max_length=12000)
    note: str = Field(default="", max_length=300)


def paise(value):
    try:
        number = Decimal(str(value))
        if number.is_finite() and 0 < number <= 1000000000 and number == number.quantize(Decimal(".01")):
            return int(number * 100)
    except (InvalidOperation, ValueError):
        pass
    return None


RECEIPT_TOTAL = re.compile(r"(?:grand\s+total|total(?:\s+paid)?|amount\s+paid)(?:\s*:\s*|\s+)(.+)", re.I)


def merchant_date(evidence):
    return " ".join(evidence["merchant"].casefold().split()), evidence["date"]


def read_receipt(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields = {}
    total_lines = []
    for line in lines:
        key, sep, value = line.partition(":")
        if sep:
            fields.setdefault(key.strip().lower(), set()).add(value.strip())
        total = RECEIPT_TOTAL.fullmatch(line)
        if total:
            total_lines.append(total[1])
    amounts = set()
    for value in total_lines:
        match = re.fullmatch(r"(?:INR|Rs\.?|\u20b9)\s*((?:\d+|\d{1,3}(?:,\d{2,3})+)(?:\.\d{1,2})?)", value, re.I)
        amounts.add(paise(match[1].replace(",", "")) if match else None)
    merchants = fields.get("merchant", {lines[0]} if lines else set())
    dates = fields.get("date", set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)))
    return {"merchant": next(iter(merchants)) if len(merchants) == 1 else "",
            "date": next(iter(dates)) if len(dates) == 1 else "",
            "amount": amounts.pop() if len(amounts) == 1 else None}


JURY_DATA = Path(__file__).resolve().parents[2] / "data" / "jury"


def jury_claims(resolution_demo=False):
    claims = read_expenses_csv(JURY_DATA / "claims.csv")
    if resolution_demo:
        claims.extend(read_expenses_csv(JURY_DATA / "resolution_claim.csv"))
    return claims


def evaluate(item, cap):
    evidence = item["evidence"]
    item.update(status="held", approved=0, eligible=None)
    # Ground the decision's explanation in the travel policy document rather
    # than a hardcoded string, via local retrieval (no embeddings/network).
    clause = retrieve_clause(item["category"])
    item["policy_citation"] = clause.citation
    if item["blocked"]:
        item["reason"] = item["blocked"]
    elif not evidence:
        item["reason"] = "Receipt required"
    elif merchant_date(evidence) != merchant_date(item):
        item["reason"] = "Receipt merchant or date differs from claim"
    elif evidence["amount"] is None:
        item["reason"] = "Receipt requires a positive INR total"
    else:
        limit = cap if item["category"] == "Meals" else item["claimed"]
        item["eligible"] = min(item["claimed"], evidence["amount"], limit)
        capped = item["category"] == "Meals" and min(item["claimed"], evidence["amount"]) > cap
        reason = (
            f"{clause.citation}: capped at INR {cap / 100:.2f} per claim" if capped
            else f"Receipt matches claim — {clause.citation}"
        )
        if evidence["amount"] != item["claimed"]:
            item["reason"] = "Receipt total differs from claim" + (f". {reason}" if capped else "")
        else:
            item.update(status="eligible", approved=item["eligible"], reason=reason)


def create_sheet(state, options):
    rows = []
    flags = {f.expense_id: f.problem for f in state.missing_data_flags if f.status == "NEEDS_REVIEW"}
    for exp in state.categorized_expenses:
        amount = paise(exp.amount)
        blocked = flags.get(exp.id, "")
        if exp.currency.upper() != "INR":
            blocked = "Outside INR policy"
        elif amount is None:
            blocked = "Invalid claim amount"
        item = dict(id=exp.id, merchant=exp.merchant, date=str(exp.date or ""), category=exp.category,
                    currency=exp.currency, claimed=amount, blocked=blocked, source="", evidence=None, events=[])
        if (options.demo or options.resolution_demo) and exp.id in {"MEAL-01", "TAXI-02"}:
            item["source"] = (JURY_DATA / f"{exp.id}.txt").read_text(encoding="utf-8")
            item["evidence"] = read_receipt(item["source"])
        evaluate(item, options.meal_cap * 100)
        rows.append(item)
    return {"meal_cap": options.meal_cap, "items": rows, "revision": 0,
            "resolution_demo": options.resolution_demo}


def edit_item(sheet, index, edit):
    if index < 0 or index >= len(sheet["items"]):
        raise ValueError("Unknown claim")
    item = sheet["items"][index]
    if edit.action in ("attach", "correct"):
        if not edit.text.strip() or (edit.action == "correct" and not item["source"]):
            raise ValueError("Receipt text is required")
        if edit.action == "attach" and item["source"]:
            raise ValueError("Use a correction to preserve the original receipt")
        if edit.action == "correct" and not edit.note.strip():
            raise ValueError("Explain the correction")
        if edit.action == "attach":
            item["source"] = edit.text
        item["evidence"] = read_receipt(edit.text)
        evaluate(item, sheet["meal_cap"] * 100)
    else:
        if not edit.note.strip():
            raise ValueError("Enter a decision reason")
        if edit.action == "accept":
            if item["status"] != "held" or item["eligible"] is None:
                raise ValueError("A matched receipt with a valid total is required")
            item.update(status="accepted", approved=item["eligible"])
        else:
            item.update(status="rejected", approved=0)
    item["events"].append({"action": edit.action, "note": edit.note.strip(), "text": edit.text})
    sheet["revision"] += 1


def summary(sheet):
    items = sheet["items"]
    claimed = sum(i["claimed"] or 0 for i in items if i["currency"].upper() == "INR")
    approved = sum(i["approved"] for i in items)
    return dict(claimed=claimed, approved=approved, difference=claimed-approved,
                held=sum(i["status"] == "held" for i in items))
