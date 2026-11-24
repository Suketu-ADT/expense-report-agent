import React from 'react';
import { X, PanelLeftClose, PanelLeftOpen, Receipt } from 'lucide-react';
import { NAV_ITEMS } from '../navigation';

export default function Sidebar({
  activeSection,
  onNavigate,
  collapsed,
  onToggleCollapsed,
  mobileOpen,
  onMobileClose,
}) {
  return (
    <>
      <div
        className={`sidebar-scrim ${mobileOpen ? 'visible' : ''}`}
        onClick={onMobileClose}
        aria-hidden="true"
      />

      <aside
        id="app-sidebar"
        className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'open' : ''}`}
        aria-label="Primary"
      >
        <div className="sidebar-head">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              <Receipt size={20} strokeWidth={1.8} />
            </span>
            <span className="brand-text">
              ExpenseFlow<span className="brand-ai"> AI</span>
            </span>
          </div>
          <button
            type="button"
            className="icon-btn sidebar-close"
            onClick={onMobileClose}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Sections">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = activeSection === item.id;
            return (
              <a
                key={item.id}
                href={`#${item.id}`}
                className={`nav-item ${active ? 'active' : ''}`}
                aria-current={active ? 'location' : undefined}
                title={collapsed ? item.label : undefined}
                onClick={(e) => {
                  e.preventDefault();
                  onNavigate(item.id);
                }}
              >
                <Icon size={17} aria-hidden="true" />
                <span className="nav-label">{item.label}</span>
              </a>
            );
          })}
        </nav>

        <div className="sidebar-foot">
          <button
            type="button"
            className="sidebar-collapse"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-pressed={collapsed}
          >
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
            <span className="nav-label">Collapse</span>
          </button>
        </div>
      </aside>
    </>
  );
}
