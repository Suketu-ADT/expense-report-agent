import React from 'react';
import { AlertTriangle } from 'lucide-react';

export default function ReviewPanel({ data }) {
  const flags = data?.missing_data_flags || [];
  const expenses = data?.categorized_expenses || [];

  if (flags.length === 0) {
    return (
      <div>
        <h3 style={{ marginTop: 0, marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>REVIEW PANEL</h3>
        <div style={{ textAlign: 'center', color: 'var(--success-color)', padding: '2rem 0' }}>
          No items require review.
        </div>
      </div>
    );
  }

  return (
    <div>
      <h3 style={{ marginTop: 0, marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>REVIEW PANEL</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {flags.map((flag, i) => {
          const exp = expenses.find(e => e.id === flag.expense_id) || data.filtered_expenses?.find(e => e.id === flag.expense_id);
          const amount = exp && exp.amount !== null ? `₹${exp.amount}` : 'Unknown Amount';
          const merchant = exp ? exp.merchant : 'Unknown Merchant';
          
          return (
            <div key={i} style={{ 
              background: 'rgba(255, 255, 255, 0.05)', 
              borderRadius: '8px', 
              padding: '1rem',
              borderLeft: `4px solid ${flag.status === 'EXCLUDED' ? 'var(--error-color)' : 'var(--warning-color)'}`
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontWeight: 600 }}>
                <AlertTriangle size={16} color={flag.status === 'EXCLUDED' ? 'var(--error-color)' : 'var(--warning-color)'} />
                {merchant} - {amount}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <strong>Problem:</strong> {flag.problem}<br/>
                <strong>Status:</strong> {flag.status === 'EXCLUDED' ? 'Excluded' : 'Needs Review'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
