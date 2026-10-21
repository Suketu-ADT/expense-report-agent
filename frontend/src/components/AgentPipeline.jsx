import React, { useState } from 'react';
import {
  Settings, Database, Filter, Tag, Calculator, ShieldCheck, RefreshCw, FileText, HardDrive, Send,
  Circle, Loader2, CheckCircle2, CircleMinus, XCircle, Hourglass, Workflow,
} from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import { formatTime, humanize } from '../utils/format';

const AGENTS = [
  { name: 'Orchestrator', icon: Settings },
  { name: 'Data Retrieval', icon: Database },
  { name: 'Filter & Validation', icon: Filter },
  { name: 'Categorization', icon: Tag },
  { name: 'Calculation', icon: Calculator },
  { name: 'Expense Review', icon: ShieldCheck },
  { name: 'Correction', icon: RefreshCw },
  { name: 'Report Generation', icon: FileText },
  { name: 'Memory Persistence', icon: HardDrive },
  { name: 'Email Dispatch', icon: Send },
];

const STATE_META = {
  pending: { label: 'Pending', icon: Circle, tone: 'neutral' },
  running: { label: 'Running', icon: Loader2, tone: 'info' },
  completed: { label: 'Completed', icon: CheckCircle2, tone: 'success' },
  skipped: { label: 'Skipped', icon: CircleMinus, tone: 'neutral' },
  'not-needed': { label: 'Not needed', icon: CircleMinus, tone: 'neutral' },
  failed: { label: 'Failed', icon: XCircle, tone: 'error' },
  'waiting-approval': { label: 'Waiting for approval', icon: Hourglass, tone: 'warning' },
  rejected: { label: 'Rejected by reviewer', icon: XCircle, tone: 'error' },
};

/**
 * Status resolution is unchanged from the original component: the backend's
 * agent_status wins, then a small number of documented fallbacks. Only the
 * returned keys were renamed for display ("waiting" is shown as "Pending").
 */
function resolveStage(data, agentName) {
  if (!data) return 'pending';

  // A reviewer's rejection is recorded in approval_status; the stage's own
  // status can still read WAITING, which would wrongly suggest it may proceed.
  if (
    agentName === 'Email Dispatch' &&
    data.approval_status === 'rejected' &&
    data.delivery_status !== 'delivered' &&
    data.agent_status?.['Email Dispatch'] !== 'COMPLETED'
  ) {
    return 'rejected';
  }

  const raw = data.agent_status ? data.agent_status[agentName] : null;
  if (raw) {
    const lower = raw.toLowerCase();
    if (lower === 'completed') return 'completed';
    if (lower === 'running') return 'running';
    if (lower === 'failed') return 'failed';
    if (lower === 'skipped') return 'skipped';
    if (lower === 'waiting') return 'waiting-approval';
  }

  if (data.current_agent === agentName && data.status === 'running') return 'running';

  if (agentName === 'Correction') {
    if (data.agent_status?.['Correction'] === 'COMPLETED') return 'completed';
    if (data.review_result?.overall_status === 'passed' && (data.retry_count || 0) === 0) return 'not-needed';
  }

  if (agentName === 'Email Dispatch') {
    if (data.delivery_status === 'delivered' || data.agent_status?.['Email Dispatch'] === 'COMPLETED') return 'completed';
    if (data.delivery_status === 'failed' || data.agent_status?.['Email Dispatch'] === 'FAILED') return 'failed';
    if (data.status === 'completed' && data.approval_status !== 'approved') return 'waiting-approval';
  }

  if (data.status === 'completed' || data.status === 'failed') return 'skipped';

  return 'pending';
}

function stageLogs(logs, agentName) {
  return (logs || []).filter(
    (l) =>
      l.agent === agentName ||
      (agentName === 'Email Dispatch' && l.agent === 'System' && /^email/i.test(l.action || ''))
  );
}

// Explanations are only ever taken from what the backend returned. When it
// returned nothing, we say so rather than inventing a reason.
function reasonFor(state, data, entries, agentName) {
  const runErrors = data?.errors || [];
  const entryErrors = entries.map((e) => e.errors).filter(Boolean);
  switch (state) {
    case 'failed': {
      const msgs = entryErrors.length ? entryErrors : runErrors;
      return {
        kind: 'error',
        lines: msgs.length ? msgs : ['The backend reported a failure but did not include an error message.'],
      };
    }
    case 'skipped': {
      if (data?.agent_status?.[agentName] === 'SKIPPED') {
        return runErrors.length
          ? { kind: 'info', lines: runErrors, prefix: 'Reported by the backend:' }
          : { kind: 'info', lines: ['The backend marked this stage as skipped without giving a reason.'] };
      }
      return { kind: 'info', lines: ['The run ended without this stage reporting a status.'] };
    }
    case 'not-needed':
      return { kind: 'info', lines: ['Review passed with no corrections required.'] };
    case 'waiting-approval':
      return { kind: 'info', lines: ['Dispatch is held until a reviewer approves or rejects the report.'] };
    case 'rejected':
      return { kind: 'info', lines: ['A reviewer rejected this report, so email dispatch was cancelled.'] };
    default:
      return null;
  }
}

export default function AgentPipeline({ data, logs = [], isRunning = false }) {
  const [selected, setSelected] = useState(null);

  const stages = AGENTS.map((a) => ({ ...a, state: resolveStage(data, a.name) }));
  const completedCount = stages.filter((s) => s.state === 'completed').length;
  const hasRun = !!data || isRunning;

  const selectedStage = stages.find((s) => s.name === selected) || null;
  const entries = selectedStage ? stageLogs(logs, selectedStage.name) : [];
  const reason = selectedStage ? reasonFor(selectedStage.state, data, entries, selectedStage.name) : null;
  const stamped = entries.filter((e) => e.timestamp);
  const first = stamped[0]?.timestamp;
  const last = stamped[stamped.length - 1]?.timestamp;
  const spanSec = first && last ? Math.max(0, Math.round((new Date(last) - new Date(first)) / 1000)) : null;

  const toggle = (name) => setSelected((cur) => (cur === name ? null : name));

  return (
    <Card
      id="pipeline-card"
      title="Agent pipeline"
      description="Each stage reports its own status. Select a stage to see its log entries and any errors."
      icon={Workflow}
      actions={
        <>
          {data?.current_agent && data.status === 'running' && (
            <Badge tone="info" dot>Running: {data.current_agent}</Badge>
          )}
          <Badge tone={completedCount === AGENTS.length ? 'success' : 'neutral'}>
            {completedCount} / {AGENTS.length} completed
          </Badge>
        </>
      }
    >
      <div
        className="track"
        role="img"
        aria-label={`Execution progress: ${completedCount} of ${AGENTS.length} stages completed`}
      >
        {stages.map((s) => (
          <span key={s.name} className={`track-seg track-${s.state}`} title={`${s.name}: ${STATE_META[s.state].label}`} />
        ))}
      </div>

      {!hasRun && (
        <p className="hint">No run yet. Start the agent to watch each stage execute.</p>
      )}

      <ol className="stage-grid">
        {stages.map((s, i) => {
          const meta = STATE_META[s.state];
          const StateIcon = meta.icon;
          const AgentIcon = s.icon;
          const open = selected === s.name;
          return (
            <li key={s.name}>
              <button
                type="button"
                className={`stage stage-${s.state} ${open ? 'open' : ''}`}
                onClick={() => toggle(s.name)}
                aria-expanded={open}
                aria-controls="stage-detail"
              >
                <span className="stage-top">
                  <span className="stage-num">{String(i + 1).padStart(2, '0')}</span>
                  <span className="stage-agent-icon" aria-hidden="true"><AgentIcon size={15} /></span>
                </span>
                <span className="stage-name">{s.name}</span>
                <span className="stage-state">
                  <StateIcon size={13} className={s.state === 'running' ? 'spin' : ''} aria-hidden="true" />
                  {meta.label}
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      {selectedStage && (
        <div
          id="stage-detail"
          className={`stage-detail stage-detail-${selectedStage.state}`}
          role="region"
          aria-label={`${selectedStage.name} details`}
        >
          <div className="stage-detail-head">
            <strong>{selectedStage.name}</strong>
            <Badge tone={STATE_META[selectedStage.state].tone}>{STATE_META[selectedStage.state].label}</Badge>
            {first && (
              <span className="stage-detail-meta">
                Logged activity {formatTime(first)}{last && last !== first ? ` – ${formatTime(last)}` : ''}
                {spanSec !== null && spanSec > 0 ? ` (${spanSec}s)` : ''}
              </span>
            )}
          </div>

          {reason && (
            <div className={`stage-reason stage-reason-${reason.kind}`}>
              {reason.prefix && <div className="stage-reason-prefix">{reason.prefix}</div>}
              {reason.lines.map((l, i) => <div key={i}>{l}</div>)}
            </div>
          )}

          {entries.length > 0 ? (
            <ul className="stage-log">
              {entries.map((e, i) => (
                <li key={i}>
                  <span className="stage-log-time">{formatTime(e.timestamp) || '—'}</span>
                  <span className="stage-log-action">{e.action}</span>
                  <span className={`stage-log-status log-${(e.status || '').toLowerCase()}`}>{humanize(e.status)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="hint hint-flush">No log entries have been recorded for this stage yet.</p>
          )}
        </div>
      )}
    </Card>
  );
}
