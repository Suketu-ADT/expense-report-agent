import React, { useRef, useEffect } from 'react';

export default function RunLog({ logs }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const formatTime = (ts) => {
    if (!ts) return '';
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div>
      <h3 style={{ marginTop: 0, marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>AGENT RUN LOG</h3>
      <div className="log-container" ref={containerRef}>
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-secondary)' }}>Waiting for logs...</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="log-entry">
              <span className="log-time">{formatTime(log.timestamp)}</span>
              <span className="log-agent">{log.agent}</span>
              <span className="log-action">{log.action}</span>
              <span className={`log-status ${log.status?.toLowerCase()}`}>{log.status}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
