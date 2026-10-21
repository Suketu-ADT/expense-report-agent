import React from 'react';

/**
 * Standard surface used by every dashboard section.
 * Purely presentational: title row, optional actions, body.
 */
export default function Card({
  id,
  title,
  description,
  icon: Icon,
  actions,
  children,
  className = '',
  bodyClassName = '',
  flush = false,
}) {
  const titleId = id ? `${id}-title` : undefined;
  return (
    <section id={id} className={`card ${className}`} aria-labelledby={titleId}>
      {(title || actions) && (
        <header className="card-header">
          <div className="card-heading">
            {Icon && (
              <span className="card-icon" aria-hidden="true">
                <Icon size={16} />
              </span>
            )}
            <div className="card-heading-text">
              {title && <h3 id={titleId} className="card-title">{title}</h3>}
              {description && <p className="card-description">{description}</p>}
            </div>
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      <div className={`card-body ${flush ? 'card-body-flush' : ''} ${bodyClassName}`}>{children}</div>
    </section>
  );
}
