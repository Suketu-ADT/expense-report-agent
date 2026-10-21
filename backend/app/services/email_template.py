"""
HTML email body for the expense report.

Mirrors the dashboard's "Expense Reports" section: headline figures, an itemized
expenses table (including excluded records) and a category breakdown.
Table-based layout with inline styles only, because email clients ignore most CSS.
All figures come from the report state; nothing is computed beyond sums/shares
of values already in it.
"""
from datetime import datetime
from html import escape

from app.state.blackboard import ExpenseReportState

SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
PALETTE = ["#635BFF", "#16845B", "#B7791F", "#C43D4B", "#0E7490", "#8B5CF6", "#64748B", "#BE185D"]

INK = "#171923"
MUTED = "#687083"
LINE = "#E7E9F0"
BG = "#F7F8FC"


def _group(integer_digits: str, indian: bool) -> str:
    if not indian or len(integer_digits) <= 3:
        return f"{int(integer_digits):,}" if not indian else integer_digits
    head, tail = integer_digits[:-3], integer_digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def number(value, indian: bool = True) -> str:
    """12345.5 -> '12,345.50' (Indian lakh grouping when indian=True)."""
    if value is None:
        return "N/A"
    neg = value < 0
    whole, frac = f"{abs(value):.2f}".split(".")
    return f"{'-' if neg else ''}{_group(whole, indian)}.{frac}"


def money(value, code: str | None) -> str:
    if value is None:
        return "N/A"
    if not code:
        return number(value)
    code = code.upper()
    sym = SYMBOLS.get(code)
    return f"{sym}{number(value, indian=(code == 'INR'))}" if sym else f"{code} {number(value, indian=False)}"


def _run_currency(state: ExpenseReportState):
    records = state.filtered_expenses or state.categorized_expenses or state.raw_expenses
    codes = sorted({(e.currency or "").upper() for e in records if e.currency})
    if len(codes) == 1:
        return codes[0], codes
    if not codes:
        return "INR", codes
    return None, codes  # mixed: totals are unconverted sums


def _date(d) -> str:
    return d.strftime("%d %b %Y") if d else "N/A"


def _badge(label: str, fg: str, bg: str) -> str:
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:10px;'
        f'font-size:11px;font-weight:600;color:{fg};background:{bg};white-space:nowrap;">{escape(label)}</span>'
    )


def _status(flag):
    if flag is None:
        return _badge("Valid", "#0F6B49", "#E6F4EE"), ""
    if flag.status == "EXCLUDED":
        label = "Duplicate · excluded" if flag.problem == "Duplicate" else "Excluded"
        return _badge(label, "#A12F3C", "#FEE6E8"), "#FEF4F5"
    if flag.status == "RESOLVED":
        return _badge("Resolved", "#4A42E0", "#EEEDFF"), ""
    return _badge("Needs review", "#85560F", "#FEF3E7"), "#FFFAF3"


def _metric(label: str, value: str, color: str) -> str:
    return (
        f'<td width="25%" style="padding:14px 16px;border:1px solid {LINE};border-radius:8px;background:#FFFFFF;" valign="top">'
        f'<div style="font-size:12px;color:{MUTED};">{escape(label)}</div>'
        f'<div style="font-size:20px;font-weight:700;color:{color};padding-top:4px;">{value}</div></td>'
    )


def build_expense_report_html(state: ExpenseReportState) -> str:
    code, codes = _run_currency(state)
    period = state.date_range.start_date.strftime("%B %Y") if state.date_range else "Unknown Period"

    confirmed = state.totals.get("confirmed_total", 0.0)
    provisional = state.provisional_totals.get("provisional_total", 0.0)
    needs_review = [f for f in state.missing_data_flags if f.status == "NEEDS_REVIEW"]
    flag_by_id = {}
    for f in state.missing_data_flags:
        flag_by_id.setdefault(f.expense_id, f)

    # Itemized rows: categorized records, then excluded records (e.g. duplicates)
    # taken from the raw data so nothing the validation agent rejected is hidden.
    rows = [(e, flag_by_id.get(e.id), e.category) for e in state.categorized_expenses]
    shown = {e.id for e in state.categorized_expenses}
    raw_by_id = {e.id: e for e in state.raw_expenses}
    for f in state.missing_data_flags:
        if f.status == "EXCLUDED" and f.expense_id not in shown and f.expense_id in raw_by_id:
            shown.add(f.expense_id)
            rows.append((raw_by_id[f.expense_id], f, "—"))

    n_excluded = sum(1 for _, f, _ in rows if f and f.status == "EXCLUDED")
    sub = f"{len(rows)} records · {len(needs_review)} need review · {n_excluded} excluded"

    # ── Itemized expenses table ─────────────────────────────────────────
    th = f'style="padding:8px 10px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:{MUTED};background:{BG};border-top:1px solid {LINE};border-bottom:1px solid {LINE};text-align:%s;"'
    head = (
        f"<tr><th {th % 'left'}>Date</th><th {th % 'left'}>Merchant</th><th {th % 'left'}>Category</th>"
        f"<th {th % 'right'}>Amount</th><th {th % 'left'}>Currency</th><th {th % 'left'}>Status</th></tr>"
    )
    body_rows = []
    for exp, flag, category in rows:
        badge, tint = _status(flag)
        td = f"padding:9px 10px;border-bottom:1px solid {LINE};font-size:13px;color:{INK};vertical-align:top;"
        bg = f"background:{tint};" if tint else ""
        problem = (
            f'<div style="font-size:11px;color:#85560F;padding-top:2px;">{escape(flag.problem)}</div>'
            if flag and flag.status != "RESOLVED" else ""
        )
        body_rows.append(
            f'<tr style="{bg}">'
            f'<td style="{td}white-space:nowrap;">{_date(exp.date)}</td>'
            f'<td style="{td}"><div style="font-weight:600;">{escape(exp.merchant)}</div>{problem}</td>'
            f'<td style="{td}">{escape(category or "—")}</td>'
            f'<td style="{td}text-align:right;white-space:nowrap;font-weight:600;">{number(exp.amount, indian=(exp.currency or "").upper() == "INR")}</td>'
            f'<td style="{td}font-family:Consolas,monospace;font-size:12px;">{escape(exp.currency or "")}</td>'
            f'<td style="{td}">{badge}</td></tr>'
        )
    if not body_rows:
        body_rows.append(f'<tr><td colspan="6" style="padding:20px;text-align:center;color:{MUTED};font-size:13px;">No expenses found.</td></tr>')

    # ── Category breakdown ──────────────────────────────────────────────
    cats = [(k, v) for k, v in state.totals.items() if k != "confirmed_total" and v > 0]
    cat_sum = sum(v for _, v in cats)
    cat_rows = []
    for i, (name, val) in enumerate(cats):
        pct = (val / cat_sum * 100) if cat_sum else 0
        color = PALETTE[i % len(PALETTE)]
        cat_rows.append(
            f'<tr><td style="padding:8px 0;border-bottom:1px solid {LINE};font-size:13px;color:{INK};" width="34%">'
            f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:{color};margin-right:8px;"></span>{escape(name)}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid {LINE};" width="34%">'
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>'
            f'<td width="{max(pct, 1):.0f}%" style="background:{color};height:8px;font-size:0;line-height:0;border-radius:4px;">&nbsp;</td>'
            f'<td style="font-size:0;line-height:0;">&nbsp;</td></tr></table></td>'
            f'<td style="padding:8px 0;border-bottom:1px solid {LINE};font-size:12px;color:{MUTED};text-align:right;" width="10%">{pct:.0f}%</td>'
            f'<td style="padding:8px 0 8px 12px;border-bottom:1px solid {LINE};font-size:13px;font-weight:600;color:{INK};text-align:right;white-space:nowrap;" width="22%">{money(val, code)}</td></tr>'
        )
    if not cat_rows:
        cat_rows.append(f'<tr><td style="padding:16px;text-align:center;color:{MUTED};font-size:13px;">No confirmed category totals.</td></tr>')

    # ── Needs review ────────────────────────────────────────────────────
    review_block = ""
    if needs_review:
        items = "".join(
            f'<tr><td style="padding:6px 0;border-bottom:1px solid {LINE};font-size:13px;color:{INK};">'
            f'<strong>{escape(f.expense_id)}</strong> — {escape(f.problem)}'
            f'<div style="font-size:12px;color:{MUTED};">Action: {escape(f.action_required)}</div></td></tr>'
            for f in needs_review
        )
        review_block = (
            f'<tr><td style="padding:24px 0 0;"><div style="font-size:16px;font-weight:600;color:{INK};padding-bottom:6px;">Needs review</div>'
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{items}</table></td></tr>'
        )

    mixed_note = (
        f'<div style="font-size:12px;color:#85560F;padding-top:8px;">Amounts span {", ".join(codes)} and are not converted.</div>'
        if code is None else ""
    )

    status_line = ""
    if state.review_result:
        status_line = f' · Review: {escape(state.review_result.overall_status.replace("_", " "))}'
    report_ref = f" · {escape(state.report_id)}" if state.report_id else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{BG};font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{BG};"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="680" cellspacing="0" cellpadding="0" style="max-width:680px;width:100%;">

<tr><td style="padding:0 0 16px;">
  <div style="font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:{MUTED};">Expense Reports</div>
  <div style="font-size:24px;font-weight:700;color:{INK};padding-top:4px;">Travel Expense Report — {escape(period)}</div>
  <div style="font-size:13px;color:{MUTED};padding-top:4px;">Generated {datetime.now().strftime('%d %b %Y, %H:%M')}{report_ref}{status_line}</div>
</td></tr>

<tr><td style="padding:0 0 20px;">
  <table role="presentation" width="100%" cellspacing="8" cellpadding="0" style="margin:-8px;"><tr>
    {_metric("Confirmed total", money(confirmed, code), "#0F6B49")}
    {_metric("Provisional total", money(provisional, code), "#85560F")}
    {_metric("Total expenses", str(len(state.filtered_expenses)), INK)}
    {_metric("Needs review", str(len(needs_review)), "#A12F3C" if needs_review else INK)}
  </tr></table>
  {mixed_note}
</td></tr>

<tr><td style="background:#FFFFFF;border:1px solid {LINE};border-radius:12px;padding:16px 4px 4px;">
  <div style="padding:0 16px 10px;"><div style="font-size:16px;font-weight:600;color:{INK};">Itemized expenses</div>
  <div style="font-size:13px;color:{MUTED};">{sub}</div></div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">{head}{''.join(body_rows)}</table>
</td></tr>

<tr><td style="height:16px;font-size:0;">&nbsp;</td></tr>

<tr><td style="background:#FFFFFF;border:1px solid {LINE};border-radius:12px;padding:16px 20px 12px;">
  <div style="font-size:16px;font-weight:600;color:{INK};">Category breakdown</div>
  <div style="font-size:13px;color:{MUTED};padding-bottom:8px;">Confirmed spend by category · categorised total {money(cat_sum, code)}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">{''.join(cat_rows)}</table>
</td></tr>

{review_block}

<tr><td style="padding:20px 0 0;font-size:12px;color:{MUTED};">The full PDF report is attached. Sent by ExpenseFlow AI.</td></tr>
</table></td></tr></table></body></html>"""
