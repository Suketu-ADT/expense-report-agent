import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';

const ICONS = { success: CheckCircle2, warning: AlertTriangle, error: XCircle, info: Info };

/** Inline feedback message. role=alert for errors so assistive tech announces it. */
export default function Notice({ tone = 'info', title, children, className = '' }) {
  const Icon = ICONS[tone] || Info;
  return (
    <div className={`notice notice-${tone} ${className}`} role={tone === 'error' ? 'alert' : 'status'}>
      <Icon size={16} className="notice-icon" aria-hidden="true" />
      <div className="notice-body">
        {title && <div className="notice-title">{title}</div>}
        {children && <div className="notice-text">{children}</div>}
      </div>
    </div>
  );
}
