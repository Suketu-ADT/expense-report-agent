// Presentation-only helpers. Nothing here changes or fabricates data: every
// function either formats a value it was given or reports that it is unknown.

const FALLBACK_CURRENCY = 'INR';

/**
 * Work out which currency a run's figures are in, from the expense records the
 * backend returned. The backend sums amounts without conversion, so when the
 * records span several currencies we say so instead of attaching one symbol.
 */
export function getRunCurrency(data) {
  const sources = [data?.filtered_expenses, data?.categorized_expenses, data?.raw_expenses];
  const records = sources.find((list) => Array.isArray(list) && list.length > 0) || [];
  const codes = [...new Set(records.map((e) => (e.currency || '').toUpperCase()).filter(Boolean))];
  if (codes.length === 0) return { code: FALLBACK_CURRENCY, mixed: false, codes: [] };
  if (codes.length === 1) return { code: codes[0], mixed: false, codes };
  return { code: null, mixed: true, codes };
}

const formatterCache = new Map();

function getFormatter(code) {
  if (!formatterCache.has(code)) {
    let fmt;
    try {
      fmt = new Intl.NumberFormat(code === 'INR' ? 'en-IN' : 'en-US', {
        style: 'currency',
        currency: code,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    } catch {
      fmt = null;
    }
    formatterCache.set(code, fmt);
  }
  return formatterCache.get(code);
}

/** Format an amount in a currency code. Returns an em dash for unknown values. */
export function formatMoney(value, code = FALLBACK_CURRENCY) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  if (!code) {
    return new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
  }
  const fmt = getFormatter(code.toUpperCase());
  return fmt ? fmt.format(n) : `${code} ${n.toFixed(2)}`;
}

/** Format an amount for a run-level currency descriptor from getRunCurrency. */
export function formatRunMoney(value, currency) {
  return formatMoney(value, currency?.mixed ? null : currency?.code ?? FALLBACK_CURRENCY);
}

export function formatDate(value) {
  if (!value) return '—';
  // Date-only strings (YYYY-MM-DD) are calendar dates, not instants: build them
  // in local time so they never shift by a day in negative-offset time zones.
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
  const d = m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function formatDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

export function formatTime(value) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

/** snake_case / SCREAMING_CASE -> "Sentence case". */
export function humanize(value) {
  if (!value) return '';
  const s = String(value).replace(/_/g, ' ').toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** "2026-07-01" -> "July 2026", using local calendar parsing (see formatDate). */
export function formatMonthYear(value) {
  if (!value) return '';
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
  const d = m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString('default', { month: 'long', year: 'numeric' });
}
