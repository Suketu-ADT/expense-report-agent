import React from 'react';
import { Menu, RefreshCw, ChevronRight } from 'lucide-react';

export default function TopBar({
  sectionLabel,
  runStatus,
  onOpenNav,
  onRefresh,
  isRefreshing,
}) {
  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <button
          type="button"
          className="icon-btn mobile-nav-btn"
          onClick={onOpenNav}
          aria-label="Open navigation"
          aria-controls="app-sidebar"
        >
          <Menu size={18} />
        </button>
        <nav className="breadcrumb" aria-label="Breadcrumb">
          <span className="breadcrumb-root">ExpenseFlow AI</span>
          <ChevronRight size={14} aria-hidden="true" />
          <span className="breadcrumb-current" aria-current="page">{sectionLabel}</span>
        </nav>
      </div>

      <div className="top-bar-actions">
        <div className={`system-status system-status-${runStatus.tone}`} role="status" aria-live="polite">
          <span className={`status-dot status-dot-${runStatus.tone}`} aria-hidden="true" />
          <span className="system-status-text">{runStatus.detail || runStatus.label}</span>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Re-fetch the current run and the report history from the backend"
        >
          <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} aria-hidden="true" />
          <span className="btn-label-hide-sm">{isRefreshing ? 'Refreshing…' : 'Refresh'}</span>
        </button>
      </div>
    </header>
  );
}
