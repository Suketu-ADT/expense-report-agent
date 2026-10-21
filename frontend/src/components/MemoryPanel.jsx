import React from 'react';
import { Database, Brain } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import EmptyState from './ui/EmptyState';
import { formatMoney, formatDateTime, humanize } from '../utils/format';

export default function MemoryPanel({ data, isRunning }) {
  const ctx = data?.historical_context;
  const prior = Array.isArray(ctx?.prior_reports_for_period) ? ctx.prior_reports_for_period : [];
  const prefs = ctx?.user_preferences && typeof ctx.user_preferences === 'object' ? Object.entries(ctx.user_preferences) : [];

  return (
    <Card
      id="memory-card"
      title="Memory recall"
      description="What the Orchestrator retrieved from persistent memory at the start of the run."
      icon={Brain}
      actions={ctx && !ctx.error ? <Badge tone={ctx.prior_report_count > 0 ? 'info' : 'neutral'}>{ctx.prior_report_count ?? 0} prior report{ctx.prior_report_count === 1 ? '' : 's'}</Badge> : null}
    >
      {!ctx ? (
        <EmptyState icon={Database} title={isRunning ? 'Waiting for memory recall…' : 'No memory recall yet'}>
          {isRunning
            ? 'The Orchestrator checks saved reports before the run begins.'
            : 'Run the agent to see which saved reports and preferences were recalled for the period.'}
        </EmptyState>
      ) : (
        <>
          {prior.length === 0 && prefs.length === 0 && (
            <EmptyState icon={Database} compact title={ctx.error ? 'Memory recall failed' : 'No prior reports for this period'}>
              {ctx.error || 'Nothing was recalled from persistent memory for this run.'}
            </EmptyState>
          )}

          {prior.length > 0 && (
            <div className="memory-block">
              <h4 className="subhead">Recalled reports for this period</h4>
              <ul className="recall-list">
                {prior.map((r) => (
                  <li key={r.report_id}>
                    <span className="mono recall-id">{r.report_id}</span>
                    <span className="recall-period">{r.period_label}</span>
                    <span className="recall-amount num">{formatMoney(r.confirmed_total)}</span>
                    <Badge tone={r.review_status === 'passed' ? 'success' : 'neutral'}>{humanize(r.review_status) || 'Pending'}</Badge>
                    <span className="recall-date">{formatDateTime(r.created_at)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {prefs.length > 0 && (
            <div className="memory-block">
              <h4 className="subhead">Stored user preferences</h4>
              <dl className="pref-list">
                {prefs.map(([k, v]) => (
                  <div key={k}><dt>{humanize(k)}</dt><dd>{String(v)}</dd></div>
                ))}
              </dl>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
