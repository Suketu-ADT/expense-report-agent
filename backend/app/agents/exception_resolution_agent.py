"""Find missing evidence and route each held claim by its verification result."""

from collections import defaultdict

from app.agents.evidence_review_agent import verify_receipt
from app.services.llm_service import debate_receipt_match
from app.services.reimbursement import ItemEdit, edit_item, merchant_date, read_receipt


def _attach_candidate(sheet, index, item, upload, revision, attachments, used, candidate, decision, action):
    """Run the one deterministic check that ever decides a claim either way
    (verify_receipt) against `upload`, and attach it if it clears. Used for
    both the single-candidate path and a debate's winning candidate — the
    debate only ever picks *which* receipt to try here; this check is the
    only thing that can actually approve or hold the claim."""
    attach, approved, verification = verify_receipt(sheet, index, upload.source)
    decision.update(action=action, verification=verification)
    if attach:
        edit_item(sheet, index, ItemEdit(revision=revision, action="attach", text=upload.source))
        expected_status = "held" if approved is None else "eligible"
        if item["status"] != expected_status or item["approved"] != (approved or 0):
            raise ValueError("The reimbursement calculation disagrees with the evidence review.")
        if approved is not None:
            decision["outcome"] = "resolved"
        attachments[index] = upload
        used.add(candidate)


def resolve_receipts(sheet, uploads, file_results):
    claims = defaultdict(list)
    for index, item in enumerate(sheet["items"]):
        if item["status"] == "held" and not item["source"] and not item["blocked"]:
            claims[merchant_date(item)].append(index)

    candidates = defaultdict(list)
    used = set()
    unique = []
    seen = set()
    for upload in uploads:
        if upload.content in seen:
            file_results.append({"name": upload.name, "message": "Duplicate file skipped."})
            continue
        seen.add(upload.content)
        unique.append(upload)
        fields = read_receipt(upload.source)
        key = merchant_date(fields)
        if all(key):
            candidates[key].append(len(unique) - 1)

    revision = sheet["revision"]
    decisions = []
    attachments = {}
    for index, item in enumerate(sheet["items"]):
        if item["status"] != "held":
            continue
        decision = {"index": index, "claim_id": item["id"], "outcome": "escalated"}
        if item["source"]:
            source = next((event["text"] for event in reversed(item["events"]) if event.get("text")), item["source"])
            _, _, decision["verification"] = verify_receipt(sheet, index, source)
            decision["action"] = "Rechecked evidence already attached."
        elif item["blocked"]:
            decision.update(action="Routed the claim to a reviewer.", verification=item["blocked"])
        else:
            key = merchant_date(item)
            matches = candidates[key]
            if not matches:
                decision.update(action="Searched the receipt batch.",
                                verification="Provide a receipt showing this merchant and date.")
            elif len(matches) > 1 or len(claims[key]) > 1:
                # Ambiguous — this always stays a human call; the claim is
                # never auto-attached or auto-approved from here. When
                # there are exactly two receipt candidates for one
                # unambiguous claim, two LLM advocates each argue for one
                # candidate and a judge opines — purely as context the
                # reviewer sees alongside the claim, never as a decision.
                decision.update(action="Searched the receipt batch.",
                                verification="Multiple receipts or claims share this merchant and date. Select the receipt manually.")
                if len(matches) == 2 and len(claims[key]) == 1:
                    cand_a, cand_b = matches
                    upload_a, upload_b = unique[cand_a], unique[cand_b]
                    winner, transcript = debate_receipt_match(
                        item["merchant"], item["date"], (item["claimed"] or 0) / 100,
                        [(upload_a.name, upload_a.source), (upload_b.name, upload_b.source)],
                    )
                    if transcript:
                        decision["debate"] = {"transcript": transcript, "opinion": winner}
            else:
                candidate = matches[0]
                upload = unique[candidate]
                _attach_candidate(
                    sheet, index, item, upload, revision, attachments, used, candidate, decision,
                    action=f"Proposed {upload.name}. {upload.extraction}",
                )
        decisions.append(decision)
        item["agent_review"] = decision

    for index, upload in enumerate(unique):
        if index not in used:
            file_results.append({"name": upload.name, "message": f"{upload.extraction} No verified assignment."})
    sheet["receipt_review"] = {"claims": decisions, "files": file_results}
    sheet["revision"] = revision + 1
    return attachments
