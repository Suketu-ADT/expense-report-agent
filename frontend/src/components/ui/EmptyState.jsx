import React from 'react';

export default function EmptyState({ icon: Icon, title, children, tone = 'neutral', compact = false }) {
  return (
    <div className={`empty-state empty-${tone} ${compact ? 'empty-compact' : ''}`}>
      {Icon && (
        <span className="empty-icon" aria-hidden="true">
          <Icon size={18} />
        </span>
      )}
      <div className="empty-title">{title}</div>
      {children && <div className="empty-text">{children}</div>}
    </div>
  );
}
