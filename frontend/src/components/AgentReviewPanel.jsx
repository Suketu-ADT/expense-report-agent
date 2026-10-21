import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, XCircle, CheckCircle2, ArrowRight, MessageSquare, ChevronDown, Loader2 } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import EmptyState from './ui/EmptyState';
import { humanize, formatTime } from '../utils/format';

// Wording follows the review states the backend actually emits.
const OVERALL = {
  passed: { icon: CheckCircle2, tone: 'success', label: 'Review passed' },
  needs_correction: { icon: AlertTriangle, tone: 'warning', label: 'Correction required' },
  needs_human_review: { icon: XCircle, tone: 'error', label: 'Escalated for human review' },
};
const PENDING = { icon: ShieldCheck, tone: 'neutral', label: 'Review pending' };

const SEVERITY_TONE = { critical: 'error', warning: 'warning', info: 'info' };
const RESOLUTION_TONE = { resolved: 'success', escalated: 'error', unresolved: 'warning' };
const MESSAGE_TONE = { correction_request: 'warning', correction_result: 'success', finding: 'info', info: 'neutral' };

function renderValue(v) {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

function Message({ msg }) {
  const [open, setOpen] = useState(false);
  const findings = Array.isArray(msg.findings) ? msg.findings : [];
  const hasDetail = findings.length > 0 || !!msg.task_id;
  return (
    <li className="msg">
      <div className="msg-route">
        <span className="msg-agent">{msg.sender}</span>
        <ArrowRight size={13} aria-hidden="true" />
        <span className="msg-agent msg-agent-to">{msg.recipient}</span>
        <span className="msg-badges">
          <Badge tone={MESSAGE_TONE[msg.message_type] || 'neutral'}>{humanize(msg.message_type)}</Badge>
          {msg.status && <Badge tone={msg.status === 'resolved' ? 'success' : 'neutral'}>{humanize(msg.status)}</Badge>}
        </span>
      </div>
      {msg.requested_action && <p className="msg-action"><span className="msg-key">Requested action</span> {msg.requested_action}</p>}
      <div className="msg-foot">
        {msg.timestamp && <span className="msg-time">{formatTime(msg.timestamp)}</span>}
        {hasDetail && (
          <button type="button" className="link-btn" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
            <ChevronDown size={12} className={open ? 'flip' : ''} aria-hidden="true" />
            {open ? 'Hide details' : `Details${findings.length ? ` (${findings.length} finding${findings.length === 1 ? '' : 's'})` : ''}`}
          </button>
        )}
      </div>
      {open && (
        <div className="msg-detail">
          {msg.task_id && <div className="kv"><span>Task</span><span className="mono">{msg.task_id}</span></div>}
          {findings.map((f, i) => (
            <div key={i} className="msg-finding">
              {Object.entries(f).map(([k, v]) => (
                <div key={k} className="kv"><span>{humanize(k)}</span><span>{renderValue(v)}</span></div>
              ))}
            </div>
          ))}
        </div>
      )}
    </li>
  );
}

export default function AgentReviewPanel({ data, isRunning }) {
  const reviewResult = data?.review_result;
  const messages = data?.agent_messages || [];
  const retryCount = data?.retry_count || 0;
  const escalated = !!data?.needs_human_review;

  if (!reviewResult) {
    return (
      <Card id="agent-review" title="Expense review" description="Independent check of totals, duplicates and categories." icon={ShieldCheck}>
        <EmptyState icon={isRunning ? Loader2 : ShieldCheck} title={isRunning ? 'Waiting for the Expense Review stage…' : 'Review has not been performed yet'}>
          {isRunning ? 'Findings appear here when the review agent finishes.' : 'Run the agent to see review findings and agent communication.'}
        </EmptyState>
      </Card>
    );
  }

  const info = OVERALL[reviewResult.overall_status] || PENDING;
  const StatusIcon = info.icon;
  const findings = reviewResult.findings || [];

  return (
    <Card
      id="agent-review"
      title="Expense review"
      description="Independent check of totals, duplicates and categories."
      icon={ShieldCheck}
    >
      <div className={`review-status review-${info.tone}`}>
        <StatusIcon size={20} aria-hidden="true" />
        <div className="review-status-text">
          <div className="review-status-label">{info.label}</div>
          <div className="review-status-sub">
            {findings.length} finding{findings.length === 1 ? '' : 's'} · {retryCount} correction retr{retryCount === 1 ? 'y' : 'ies'}
            {escalated && ' · Escalated to human review'}
          </div>
        </div>
      </div>

      {findings.length > 0 && (
        <ul className="finding-list" aria-label="Review findings">
          {findings.map((f, i) => (
            <li key={i} className={`finding finding-${SEVERITY_TONE[f.severity] || 'info'}`}>
              <div className="finding-head">
                <span className="finding-type">{humanize(f.finding_type)}</span>
                <span className="finding-badges">
                  {f.severity && <Badge tone={SEVERITY_TONE[f.severity] || 'info'}>{humanize(f.severity)}</Badge>}
                  <Badge tone={RESOLUTION_TONE[f.resolution_status] || 'neutral'} title="Correction status">
                    {humanize(f.resolution_status)}
                  </Badge>
                </span>
              </div>
              <p className="finding-desc">{f.description}</p>
              {Array.isArray(f.affected_expense_ids) && f.affected_expense_ids.length > 0 && (
                <div className="finding-affected">
                  <span className="msg-key">Affected</span>
                  {f.affected_expense_ids.map((id) => <code key={id} className="chip">{id}</code>)}
                </div>
              )}
              {(f.responsible_agent || f.requested_correction) && (
                <p className="finding-fix">
                  {f.responsible_agent && <span className="finding-agent">{f.responsible_agent}</span>}
                  {f.requested_correction && <span>{f.responsible_agent ? ': ' : ''}{f.requested_correction}</span>}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      {messages.length > 0 && (
        <div className="comm">
          <h4 className="subhead"><MessageSquare size={13} aria-hidden="true" /> Agent communication</h4>
          <ul className="msg-list">
            {messages.map((m, i) => <Message key={i} msg={m} />)}
          </ul>
        </div>
      )}
    </Card>
  );
}
