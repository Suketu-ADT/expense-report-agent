"""Review a proposed receipt against the claim and the INR policy."""

import re
from datetime import date

from app.services.reimbursement import merchant_date, read_receipt


def receipt_keys(source):
    normalized = " ".join(source.casefold().split())
    keys = {("text", normalized)}
    reference = re.search(r"^receipt\s*(?:id|number|no\.?|#)\s*:?\s*([\w/-]+)\s*$", source, re.I | re.M)
    if reference:
        merchant, issued = merchant_date(read_receipt(source))
        keys.add(("reference", merchant, issued, reference[1].casefold()))
    return keys


def receipt_in_use(items, index, source):
    keys = receipt_keys(source)
    for other_index, item in enumerate(items):
        if other_index == index or not item["source"]:
            continue
        readings = [item["source"], *(event["text"] for event in item["events"] if event.get("text"))]
        if any(keys & receipt_keys(reading) for reading in readings):
            return True
    return False


def verify_receipt(sheet, index, source):
    item = sheet["items"][index]
    if receipt_in_use(sheet["items"], index, source):
        return False, None, "Receipt already supports another claim in this report."

    evidence = read_receipt(source)
    merchant, issued = merchant_date(evidence)
    try:
        valid_date = date.fromisoformat(issued).isoformat() == issued
    except ValueError:
        valid_date = False
    if not merchant or not valid_date or (merchant, issued) != merchant_date(item):
        return False, None, "Receipt merchant or date could not be verified."
    if item["blocked"] or item["currency"].upper() != "INR" or item["claimed"] is None:
        return False, None, item["blocked"] or "Claim falls outside the INR policy."
    if evidence["amount"] is None:
        return True, None, "Receipt total is unreadable or ambiguous. Confirm the total from the original receipt."
    if evidence["amount"] != item["claimed"]:
        return True, None, "Receipt total differs from the claim. Confirm whether to accept the evidenced amount."

    limit = sheet["meal_cap"] * 100 if item["category"] == "Meals" else evidence["amount"]
    return True, min(evidence["amount"], limit), "Receipt and payable amount verified against the policy."
