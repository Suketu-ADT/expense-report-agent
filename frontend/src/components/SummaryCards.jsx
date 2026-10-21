import React from 'react';
import { getRunCurrency, formatRunMoney } from '../utils/format';

/**
 * Four headline metrics. A figure is shown only once the backend has produced
 * it; until then the card shows a skeleton (while running) or an em dash.
 * Unavailable is never rendered as a zero total.
 */
export default function SummaryCards({ data, isRunning }) {
  const currency = getRunCurrency(data);
  const agentStatus = data?.agent_status || {};
  const runFinished = data?.status === 'completed' || data?.status === 'failed';

  const hasConfirmed = typeof data?.totals?.confirmed_total === 'number';
  const hasProvisional = typeof data?.provisional_totals?.provisional_total === 'number';
  const validationDone = runFinished || agentStatus['Filter & Validation'] === 'COMPLETED';
  const hasCounts = Array.isArray(data?.filtered_expenses) && validationDone;

  const confirmed = hasConfirmed ? data.totals.confirmed_total : null;
  const provisional = hasProvisional ? data.provisional_totals.provisional_total : null;
  const totalCount = hasCounts ? data.filtered_expenses.length : null;
  const reviewCount = hasCounts && Array.isArray(data?.missing_data_flags)
    ? data.missing_data_flags.filter((f) => f.status === 'NEEDS_REVIEW').length
    : null;

  const mixedNote = currency.mixed ? `Mixed currencies (${currency.codes.join(', ')}), not converted` : null;

  const cards = [
    {
      key: 'confirmed',
      label: 'Confirmed total',
      tone: 'success',
      value: confirmed === null ? null : formatRunMoney(confirmed, currency),
      note: mixedNote || 'Validated expenses only',
    },
    {
      key: 'provisional',
      label: 'Provisional total',
      tone: 'warning',
      value: provisional === null ? null : formatRunMoney(provisional, currency),
      note: mixedNote || 'Awaiting review',
    },
    {
      key: 'count',
      label: 'Total expenses',
      tone: 'accent',
      value: totalCount === null ? null : String(totalCount),
      note: 'Records after validation',
    },
    {
      key: 'review',
      label: 'Needs review',
      tone: reviewCount ? 'error' : 'neutral',
      value: reviewCount === null ? null : String(reviewCount),
      note: reviewCount === null ? 'Flagged by validation' : reviewCount > 0 ? 'Flagged by validation' : 'Nothing flagged',
    },
  ];

  return (
    <div className="metric-grid" role="group" aria-label="Financial summary">
      {cards.map((c) => (
        <div className="metric" key={c.key}>
          <div className="metric-label">
            <span className={`metric-dot metric-dot-${c.tone}`} aria-hidden="true" />
            {c.label}
          </div>
          {c.value !== null ? (
            <div className={`metric-value metric-${c.tone}`}>{c.value}</div>
          ) : isRunning ? (
            <div className="metric-value"><span className="skeleton skeleton-value" aria-label="Loading" /></div>
          ) : (
            <div className="metric-value metric-empty" aria-label="Not available">—</div>
          )}
          <div className="metric-note">{c.note}</div>
        </div>
      ))}
    </div>
  );
}
