"""Read supported receipt uploads and retain the original document."""

from dataclasses import dataclass
import re

from app.services.receipt_image import NoReceiptText, receipt_text
from app.services.reimbursement import RECEIPT_TOTAL, read_receipt

MAX_RECEIPT_BYTES = 5 * 1024 * 1024
MAX_BATCH_FILES = 500
MAX_BATCH_BYTES = 100 * 1024 * 1024


@dataclass
class ReceiptUpload:
    name: str
    content: bytes
    media_type: str
    source: str
    extraction: str


def read_upload(name, content, *, retry_ocr=False):
    if name.lower().endswith(".txt"):
        media_type = "text/plain"
        try:
            source = content.decode("utf-8-sig")
        except UnicodeError as exc:
            raise ValueError("Use a UTF-8 text receipt.") from exc
        extraction = "Text file read."
    elif content.startswith(b"%PDF-"):
        media_type = "application/pdf"
        source = receipt_text(content)
        extraction = "Digital PDF text extracted."
    else:
        media_type = "image/png" if content.startswith(b"\x89PNG") else "image/jpeg"
        source, extraction = read_photo(content, retry_ocr)
    if not source.strip() or len(source) > 12000:
        raise ValueError("Use a receipt with 1 to 12,000 characters.")
    return ReceiptUpload(name[:160], content, media_type, source, extraction)


def read_photo(content, retry):
    try:
        initial = receipt_text(content)
    except NoReceiptText:
        if not retry:
            raise
        initial = ""
    fields = read_receipt(initial)
    missing_total = not any(RECEIPT_TOTAL.fullmatch(line.strip()) for line in initial.splitlines())
    if not retry or (fields["date"] and not missing_total):
        return initial, "Image OCR completed."

    try:
        second = receipt_text(content, psm=11)
    except ValueError:
        if not initial:
            raise
        return initial, "Image OCR retry could not read the missing fields."
    retry_fields = read_receipt(second)
    stable = all(not value or value == retry_fields[key] for key, value in fields.items())
    ambiguous_amount = not missing_total and fields["amount"] is None
    ambiguous_date = not fields["date"] and len(set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", initial))) > 1
    if stable and not ambiguous_amount and not ambiguous_date and all(retry_fields.values()):
        return second, "Image OCR retried with sparse text detection and recovered the missing fields."
    return initial, "Image OCR retry could not confirm the missing fields."
