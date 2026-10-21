import React from 'react';

/** Small status pill. tone: success | warning | error | info | neutral */
export default function Badge({ tone = 'neutral', icon: Icon, dot = false, children, title }) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {dot && <span className="badge-dot" aria-hidden="true" />}
      {Icon && <Icon size={12} aria-hidden="true" />}
      {children}
    </span>
  );
}
