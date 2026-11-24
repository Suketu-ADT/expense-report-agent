import React from 'react';
import { getRunCurrency, formatMoney, formatRunMoney } from '../utils/format';

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
  const reimbursement = data?.reimbursement;

  // ── Unit II: Planning & Reasoning — only shown when the planner decided
  // the run actually needed these stages (see Orchestrator / intent).
  const anomalyCount = data?.agent_status?.['Anomaly Detection'] === 'COMPLETED' && Array.isArray(data?.categorized_expenses)
    ? data.categorized_expenses.filter((e) => e.is_anomaly).length
    : null;
  const comparison = data?.agent_status?.['Period Comparison'] === 'COMPLETED' ? data?.comparison : null;

  // ── Unit III: Tool use — only shown when a non-INR currency actually
  // triggered the Currency Conversion agent to do real work.
  const converted = data?.agent_status?.['Currency Conversion'] === 'COMPLETED' ? data?.converted_total_inr : null;
  const conversionSources = data?.currency_conversions
    ? Object.values(data.currency_conversions).map((c) => c.source)
    : [];
  const anyOfflineRate = conversionSources.includes('offline-fallback');

  const cards = reimbursement ? [
    { key: 'claimed', label: 'Claimed', value: formatMoney(reimbursement.claimed / 100) },
    { key: 'approved', label: 'Approved', value: formatMoney(reimbursement.approved / 100), tone: 'success' },
    { key: 'difference', label: 'Difference', value: formatMoney(reimbursement.difference / 100) },
    { key: 'held', label: 'Claims on hold', value: reimbursement.held, tone: reimbursement.held ? 'warning' : 'neutral' },
  ] : [
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

  if (anomalyCount !== null) {
    cards.push({
      key: 'anomalies',
      label: 'Flagged anomalies',
      tone: anomalyCount > 0 ? 'warning' : 'neutral',
      value: String(anomalyCount),
      note: `Above ${formatMoney(data?.intent?.anomaly_threshold ?? 0)}`,
    });
  }

  if (comparison) {
    cards.push(
      comparison.available
        ? {
            key: 'comparison',
            label: `vs ${comparison.previous_period}`,
            tone: comparison.delta >= 0 ? 'warning' : 'success',
            value: `${comparison.delta >= 0 ? '+' : ''}${formatMoney(comparison.delta)}`,
            note: `Was ${formatMoney(comparison.previous_total)}`,
          }
        : {
            key: 'comparison',
            label: `vs ${comparison.previous_period}`,
            tone: 'neutral',
            value: '—',
            note: 'No prior report found for that period',
          }
    );
  }

  if (converted !== null) {
    cards.push({
      key: 'converted',
      label: 'Converted total (INR)',
      tone: 'accent',
      value: formatMoney(converted),
      note: anyOfflineRate ? 'Includes an offline fallback rate' : 'Live exchange rates',
    });
  }

  return (
    <div className="metric-grid" role="group" aria-label="Financial summary">
      {cards.map((c) => (
        <div className="metric" key={c.key}>
          <div className="metric-label">
            {c.label}
          </div>
          {c.value !== null ? (
            <div className={`metric-value metric-${c.tone || 'neutral'}`}>{c.value}</div>
          ) : isRunning ? (
            <div className="metric-value"><span className="skeleton skeleton-value" aria-label="Loading" /></div>
          ) : (
            <div className="metric-value metric-empty" aria-label="Not available">—</div>
          )}
          {c.note && <div className="metric-note">{c.note}</div>}
        </div>
      ))}
    </div>
  );
}
