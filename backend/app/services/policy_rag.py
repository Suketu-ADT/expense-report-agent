"""Policy RAG service: grounds reimbursement decisions in the travel policy
document instead of a bare hardcoded string.

The policy document (`data/policy/travel_policy.md`) is chunked by section at
import time. A query (the expense's category, e.g. "Meals") is scored against
every chunk with a small local term-overlap retriever — no embedding model
or network call, so this stays within the project's 100% offline guarantee.
The best-matching chunk's section number and heading become the citation
attached to the agent's decision.

This only grounds the *explanation* shown to the reviewer; it does not change
which amount is approved — that arithmetic is untouched and still exercised
by the existing reimbursement tests.
"""
import re
from pathlib import Path
from typing import List

from pydantic import BaseModel

POLICY_FILE = Path(__file__).resolve().parents[2] / "data" / "policy" / "travel_policy.md"

_SECTION_PATTERN = re.compile(r"^## (\S+) (.+)$", re.MULTILINE)
_WORD_PATTERN = re.compile(r"[a-z0-9]+")

# Fallback copy of data/policy/travel_policy.md, used only when that file
# isn't reachable (e.g. a deployment or test harness that packages `app/`
# without `data/`). Keep this in sync with the on-disk file; the on-disk
# copy is the one to edit day to day.
_EMBEDDED_POLICY = """\
## 2.1 Meals

Meals are reimbursed up to the per-claim cap configured for the report
(the default is INR 800 per claim). A claim above the cap is reimbursed at
the cap; the difference is the traveler's responsibility. A matching receipt
showing merchant, date and total is required.

## 2.2 Lodging

Lodging is reimbursed in full against a matching receipt, with no fixed
per-night cap under this policy. Claims are still held if the receipt is
missing or its merchant, date or total does not match the claim.

## 2.3 Ground Transport

Ground transport (taxi, ride-hailing, metro, bus) is reimbursed in full
against a matching receipt, with no fixed per-trip cap under this policy.
Claims are still held if the receipt is missing or its merchant, date or
total does not match the claim.

## 2.4 Airfare

Airfare is reimbursed in full against a matching receipt for an economy or
premium-economy fare, with no fixed cap under this policy. Claims are still
held if the receipt is missing or its merchant, date or total does not match
the claim.

## 2.5 Other / Uncategorized

Expenses that could not be assigned to a known category are reimbursed in
full against a matching receipt, with no fixed cap under this policy, the
same as any other uncapped category. A reviewer may still want to confirm
the categorization itself before approving.

## 3.1 Receipt evidence requirements

Every claim needs a receipt stating the merchant, the date, and a total in
INR before it can be marked eligible. A claim with no receipt, or whose
receipt's merchant, date or total does not match the claim, is held for a
human reviewer rather than auto-approved.
"""


class PolicyClause(BaseModel):
    section: str
    heading: str
    text: str
    score: float

    @property
    def citation(self) -> str:
        return f"Travel Policy §{self.section} {self.heading}"


def _tokenize(text: str) -> List[str]:
    return _WORD_PATTERN.findall(text.lower())


def _load_chunks() -> List[PolicyClause]:
    try:
        raw = POLICY_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        raw = _EMBEDDED_POLICY
    matches = list(_SECTION_PATTERN.finditer(raw))
    chunks = []
    for i, match in enumerate(matches):
        section, heading = match.group(1), match.group(2)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[start:end].strip()
        chunks.append(PolicyClause(section=section, heading=heading, text=body, score=0.0))
    return chunks


_CHUNKS = _load_chunks()


def _score(query_tokens: List[str], chunk: PolicyClause) -> float:
    """Term-overlap score: fraction of query terms that appear in the chunk
    (heading counted twice, since it is the strongest topical signal)."""
    chunk_tokens = set(_tokenize(chunk.heading)) | set(_tokenize(chunk.heading)) | set(_tokenize(chunk.text))
    if not query_tokens:
        return 0.0
    hits = sum(1 for t in query_tokens if t in chunk_tokens)
    return hits / len(query_tokens)


def retrieve_clause(query: str) -> PolicyClause:
    """Retrieve the policy clause most relevant to `query` (typically an
    expense category, e.g. "Meals"). Always returns a clause — the lowest
    possible score is 0.0, never a missing result, so callers never need a
    None-check before citing it."""
    query_tokens = _tokenize(query)
    best = max(_CHUNKS, key=lambda c: _score(query_tokens, c))
    return best.model_copy(update={"score": _score(query_tokens, best)})
