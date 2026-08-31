import React from 'react';

export default function SummaryCards({ data }) {
  const confirmed = data?.totals?.confirmed_total || 0;
  const provisional = data?.provisional_totals?.provisional_total || 0;
  const totalCount = data?.filtered_expenses?.length || 0;
  const reviewCount = data?.missing_data_flags?.filter(f => f.status === 'NEEDS_REVIEW').length || 0;

  return (
    <>
      <div className="panel stat-card">
        <div className="stat-label">Confirmed Total</div>
        <div className="stat-value" style={{ color: 'var(--success-color)' }}>
          ₹{confirmed.toFixed(2)}
        </div>
      </div>
      <div className="panel stat-card">
        <div className="stat-label">Provisional Total</div>
        <div className="stat-value" style={{ color: 'var(--warning-color)' }}>
          ₹{provisional.toFixed(2)}
        </div>
      </div>
      <div className="panel stat-card">
        <div className="stat-label">Total Expenses</div>
        <div className="stat-value">{totalCount}</div>
      </div>
      <div className="panel stat-card">
        <div className="stat-label">Needs Review</div>
        <div className="stat-value" style={{ color: reviewCount > 0 ? 'var(--error-color)' : 'var(--text-primary)' }}>
          {reviewCount}
        </div>
      </div>
    </>
  );
}
