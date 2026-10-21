import React, { useState } from 'react';
import { CheckCircle2, XCircle, Loader2, Lock, Send } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import Notice from './ui/Notice';
import EmptyState from './ui/EmptyState';
import { humanize } from '../utils/format';

const APPROVAL_TONE = { pending: 'warning', approved: 'success', rejected: 'error' };

/**
 * Human-in-the-loop approval gate.
 *
 * Presentation only: onApprove / onReject are App's original handlers and
 * nothing is called until the reviewer clicks. The buttons are disabled for the
 * whole duration of the request, and any success message comes from App after
 * the server has answered.
 */
export default function ApprovalGate({
  data,
  runStatus,
  logs,
  approvalLoading,
  approvalMessage,
  onApprove,
  onReject,
}) {
  const [acting, setActing] = useState(null);

  // Which button was pressed only matters while a request is in flight.
  const activeAction = approvalLoading ? acting : null;

  const header = {
    id: 'approval',
    title: 'Human approval gate',
    description: 'A reviewer must approve before the report email is sent.',
    icon: Lock,
  };

  // Same visibility rule as before: the gate is actionable once the run has
  // completed and the report has not already been delivered.
  const completed = runStatus === 'completed' && !!data;

  if (!completed) {
    return (
      <Card {...header}>
        {runStatus === 'failed' ? (
          <EmptyState icon={XCircle} tone="error" title="Run failed — nothing to approve">
            Approval is only requested for a completed report.
          </EmptyState>
        ) : (
          <EmptyState icon={Lock} title={runStatus === 'running' ? 'Waiting for the report…' : 'No report awaiting approval'}>
            {runStatus === 'running'
              ? 'The approval gate opens when the run completes.'
              : 'After a report is generated, you approve or reject its email dispatch here.'}
          </EmptyState>
        )}
      </Card>
    );
  }

  const approval = data.approval_status || 'pending';
  const delivered = data.delivery_status === 'delivered';

  // Real, backend-provided explanation of why dispatch is held, if one was logged.
  const heldNote = [...(logs || [])]
    .reverse()
    .find((l) => l.agent === 'System' && /^email (held|cancelled)/i.test(l.action || ''));

  const click = (kind, fn) => () => {
    setActing(kind);
    fn();
  };

  return (
    <Card
      {...header}
      className={`approval approval-${approval}`}
      actions={<Badge tone={APPROVAL_TONE[approval] || 'neutral'} dot>Approval {humanize(approval)}</Badge>}
    >
      <div className="approval-reason">
        <div className="approval-reason-title">Why approval is required</div>
        <p>
          {data.needs_human_review
            ? 'The Expense Review agent escalated this report for human review before it can be sent.'
            : 'Email dispatch is held behind an explicit approval gate. Nothing is sent until you approve.'}
        </p>
        {heldNote && <p className="approval-note">Backend note: {heldNote.action}</p>}
      </div>

      {delivered ? (
        <Notice tone="success" title="Email delivered">
          This report has already been dispatched, so no further approval is needed.
        </Notice>
      ) : (
        <div className="approval-actions">
          <button
            type="button"
            className="btn btn-success btn-lg"
            onClick={click('approve', onApprove)}
            disabled={approvalLoading || approval === 'approved'}
          >
            {activeAction === 'approve'
              ? <Loader2 size={16} className="spin" aria-hidden="true" />
              : approval === 'approved' ? <CheckCircle2 size={16} aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
            {activeAction === 'approve'
              ? 'Dispatching…'
              : approval === 'approved' ? 'Approved & Dispatched' : 'Approve & Dispatch Email'}
          </button>
          <button
            type="button"
            className="btn btn-danger-outline btn-lg"
            onClick={click('reject', onReject)}
            disabled={approvalLoading || approval === 'rejected'}
          >
            {activeAction === 'reject'
              ? <Loader2 size={16} className="spin" aria-hidden="true" />
              : <XCircle size={16} aria-hidden="true" />}
            {activeAction === 'reject' ? 'Rejecting…' : approval === 'rejected' ? 'Rejected' : 'Reject'}
          </button>
        </div>
      )}

      {approvalMessage && (
        <Notice tone={approvalMessage.type} className="approval-feedback">
          {approvalMessage.text}
        </Notice>
      )}
    </Card>
  );
}
