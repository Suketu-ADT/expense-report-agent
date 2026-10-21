import React from 'react';
import { ListChecks, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import EmptyState from './ui/EmptyState';
import { formatMoney } from '../utils/format';

/** Data-quality flags raised by Filter & Validation. Lookup logic is unchanged. */
export default function ReviewPanel({ data, isRunning }) {
  const flags = data?.missing_data_flags || [];
  const expenses = data?.categorized_expenses || [];

  const validationDone =
    data?.status === 'completed' || data?.status === 'failed' || data?.agent_status?.['Filter & Validation'] === 'COMPLETED';

  return (
    <Card
      id="data-quality"
      title="Data quality flags"
      description={flags.length ? `${flags.length} record${flags.length === 1 ? '' : 's'} flagged by validation` : 'Records flagged by validation.'}
      icon={ListChecks}
    >
      {flags.length === 0 ? (
        data && validationDone ? (
          <EmptyState icon={CheckCircle2} tone="success" title="No items require review">
            Validation did not flag any records.
          </EmptyState>
        ) : (
          <EmptyState icon={ListChecks} title={isRunning ? 'Waiting for validation…' : 'No data yet'}>
            Flagged records appear here after the Filter &amp; Validation stage.
          </EmptyState>
        )
      ) : (
        <ul className="flag-list">
          {flags.map((flag, i) => {
            const exp =
              expenses.find((e) => e.id === flag.expense_id) ||
              data.filtered_expenses?.find((e) => e.id === flag.expense_id) ||
              data.raw_expenses?.find((e) => e.id === flag.expense_id);
            const excluded = flag.status === 'EXCLUDED';
            const resolved = flag.status === 'RESOLVED';
            const Icon = resolved ? CheckCircle2 : excluded ? XCircle : AlertTriangle;
            const tone = resolved ? 'info' : excluded ? 'error' : 'warning';
            const amount = exp && exp.amount !== null && exp.amount !== undefined
              ? formatMoney(exp.amount, exp.currency)
              : 'Unknown amount';
            return (
              <li key={i} className={`flag flag-${tone}`}>
                <Icon size={15} className="flag-icon" aria-hidden="true" />
                <div className="flag-body">
                  <div className="flag-head">
                    <span className="flag-title">{exp ? exp.merchant : 'Unknown merchant'}</span>
                    <span className="flag-amount">{amount}</span>
                  </div>
                  <div className="flag-problem">{flag.problem}</div>
                  {flag.action_required && <div className="flag-action">Action: {flag.action_required}</div>}
                </div>
                <Badge tone={tone}>{resolved ? 'Resolved' : excluded ? 'Excluded' : 'Needs review'}</Badge>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
