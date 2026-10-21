import React, { useRef, useEffect, useState } from 'react';
import { ScrollText, CheckCircle2, AlertTriangle, XCircle, Info, Loader2, ChevronDown } from 'lucide-react';
import Card from './ui/Card';
import EmptyState from './ui/EmptyState';
import { formatTime, humanize } from '../utils/format';

const STATUS_META = {
  completed: { tone: 'success', icon: CheckCircle2 },
  warning: { tone: 'warning', icon: AlertTriangle },
  failed: { tone: 'error', icon: XCircle },
  running: { tone: 'info', icon: Loader2 },
  info: { tone: 'neutral', icon: Info },
};

const LONG_ACTION = 110;

export default function RunLog({ logs, isRunning }) {
  const containerRef = useRef(null);
  const [expanded, setExpanded] = useState(() => new Set());

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const toggle = (i) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  return (
    <Card
      id="runlog"
      title="Agent run log"
      description={logs.length ? `${logs.length} event${logs.length === 1 ? '' : 's'} recorded` : 'Chronological record of what each agent did.'}
      icon={ScrollText}
      flush
    >
      {logs.length === 0 ? (
        <EmptyState icon={ScrollText} title={isRunning ? 'Waiting for the first log entry…' : 'No run yet'}>
          {isRunning ? 'Entries appear here as each agent reports in.' : 'Log events from each agent will appear here once you run the agent.'}
        </EmptyState>
      ) : (
        <div className="timeline-scroll" ref={containerRef} tabIndex={0} aria-label="Agent run log entries">
          <ol className="timeline">
            {logs.map((log, i) => {
              const key = (log.status || 'info').toLowerCase();
              const meta = STATUS_META[key] || STATUS_META.info;
              const Icon = meta.icon;
              const long = (log.action || '').length > LONG_ACTION;
              const expandable = long;
              const open = expanded.has(i);
              return (
                <li key={i} className={`tl-item tl-${meta.tone}`}>
                  <span className="tl-marker" aria-hidden="true">
                    <Icon size={12} className={key === 'running' ? 'spin' : ''} />
                  </span>
                  <div className="tl-content">
                    <div className="tl-head">
                      <span className="tl-agent">{log.agent}</span>
                      <span className={`tl-status tl-status-${meta.tone}`}>{humanize(log.status)}</span>
                      <span className="tl-time">{formatTime(log.timestamp)}</span>
                    </div>
                    <p className={`tl-action ${expandable && !open ? 'clamped' : ''}`}>{log.action}</p>
                    {log.errors && <p className="tl-error">{log.errors}</p>}
                    {expandable && (
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => toggle(i)}
                        aria-expanded={open}
                      >
                        <ChevronDown size={12} className={open ? 'flip' : ''} aria-hidden="true" />
                        {open ? 'Show less' : 'Show more'}
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </Card>
  );
}
