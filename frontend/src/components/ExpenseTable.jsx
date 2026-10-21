import React from 'react';
import { Receipt } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import EmptyState from './ui/EmptyState';
import { formatDate, formatMoney } from '../utils/format';

// Same classification as before, plus RESOLVED (which the backend can emit but
// the old table lumped in with "Needs Review").
function classify(flag) {
  if (!flag) return { key: 'valid', label: 'Valid', tone: 'success' };
  if (flag.status === 'EXCLUDED') return { key: 'excluded', label: flag.problem === 'Duplicate' ? 'Duplicate · excluded' : 'Excluded', tone: 'error' };
  if (flag.status === 'RESOLVED') return { key: 'resolved', label: 'Resolved', tone: 'info' };
  return { key: 'review', label: 'Needs review', tone: 'warning' };
}

export default function ExpenseTable({ data, isRunning }) {
  const categorized = data?.categorized_expenses || [];
  const flags = data?.missing_data_flags || [];
  const raw = data?.raw_expenses || [];

  const flagFor = (id) => flags.find((f) => f.expense_id === id);

  const rows = categorized.map((exp) => ({ exp, flag: flagFor(exp.id), fromRaw: false }));

  // Excluded records (e.g. duplicates) never reach categorized_expenses. Show
  // them from the raw records, using the backend's own flag, so nothing the
  // validation agent rejected disappears from view.
  const shown = new Set(categorized.map((e) => e.id));
  flags
    .filter((f) => f.status === 'EXCLUDED' && !shown.has(f.expense_id))
    .forEach((f) => {
      const exp = raw.find((e) => e.id === f.expense_id);
      if (exp && !shown.has(exp.id)) {
        shown.add(exp.id);
        rows.push({ exp, flag: f, fromRaw: true });
      }
    });

  const counts = rows.reduce(
    (acc, r) => {
      const k = classify(r.flag).key;
      acc[k] = (acc[k] || 0) + 1;
      return acc;
    },
    {}
  );

  const description = rows.length
    ? [
        `${rows.length} record${rows.length === 1 ? '' : 's'}`,
        counts.review ? `${counts.review} need review` : null,
        counts.excluded ? `${counts.excluded} excluded` : null,
      ].filter(Boolean).join(' · ')
    : 'Validated transactions with their category and review status.';

  return (
    <Card id="expenses" title="Itemized expenses" description={description} icon={Receipt} flush>
      {rows.length === 0 ? (
        <EmptyState icon={Receipt} title={data ? 'No expenses found' : isRunning ? 'Waiting for expenses…' : 'No expenses yet'}>
          {data
            ? 'The run finished without any expense records to list.'
            : 'Run the agent to retrieve, validate and categorise your expenses.'}
        </EmptyState>
      ) : (
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Itemized expenses table">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Merchant</th>
                <th scope="col">Category</th>
                <th scope="col" className="num">Amount</th>
                <th scope="col">Currency</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ exp, flag, fromRaw }, i) => {
                const status = classify(flag);
                return (
                  <tr key={`${exp.id}-${i}`} className={`row-${status.key}`}>
                    <td data-label="Date" className="nowrap">{exp.date ? formatDate(exp.date) : 'N/A'}</td>
                    <td data-label="Merchant">
                      <div className="cell-main">{exp.merchant}</div>
                      {flag && flag.status !== 'RESOLVED' && <div className="cell-sub">{flag.problem}</div>}
                    </td>
                    <td data-label="Category">{exp.category || (fromRaw ? '—' : '')}</td>
                    <td data-label="Amount" className="num">
                      {exp.amount !== null && exp.amount !== undefined ? formatMoney(exp.amount, null) : 'N/A'}
                    </td>
                    <td data-label="Currency" className="mono">{exp.currency}</td>
                    <td data-label="Status">
                      <Badge tone={status.tone} title={flag?.action_required || undefined}>{status.label}</Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
