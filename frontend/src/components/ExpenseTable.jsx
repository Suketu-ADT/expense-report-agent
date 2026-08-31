import React from 'react';

export default function ExpenseTable({ data }) {
  const expenses = data?.categorized_expenses || [];
  const flags = data?.missing_data_flags || [];

  const getStatus = (id) => {
    const flag = flags.find(f => f.expense_id === id);
    if (!flag) return { label: 'Valid', class: 'status-valid' };
    if (flag.status === 'EXCLUDED') return { label: 'Excluded', class: 'status-excluded' };
    return { label: 'Needs Review', class: 'status-review' };
  };

  return (
    <div>
      <h3 style={{ marginTop: 0, marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>ITEMIZED EXPENSES</h3>
      <div style={{ overflowX: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Merchant</th>
              <th>Category</th>
              <th>Amount</th>
              <th>Currency</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((exp, i) => {
              const statusInfo = getStatus(exp.id);
              return (
                <tr key={i} className={statusInfo.label !== 'Valid' ? 'flagged-row' : ''}>
                  <td>{exp.date || 'N/A'}</td>
                  <td>{exp.merchant}</td>
                  <td>{exp.category}</td>
                  <td>{exp.amount !== null ? exp.amount : 'N/A'}</td>
                  <td>{exp.currency}</td>
                  <td>
                    <span className={`status-badge ${statusInfo.class}`}>
                      {statusInfo.label}
                    </span>
                  </td>
                </tr>
              );
            })}
            {expenses.length === 0 && (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                  No expenses found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
