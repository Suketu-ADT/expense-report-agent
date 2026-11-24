import React, { useState } from 'react';
import { XCircle, Loader2, Lock, Send } from 'lucide-react';
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
    title: 'Email approval',
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
  const failedDelivery = data.delivery_status === 'failed';
  const held = data.reimbursement?.held || 0;
  const approvalBlocked = approvalLoading || held > 0
    || (data.reimbursement && approval === 'rejected') || (approval === 'approved' && !failedDelivery);
  const needsAttention = held > 0 || data.needs_human_review;

  const click = (kind, fn) => () => {
    setActing(kind);
    fn();
  };

  return (
    <Card
      {...header}
      className={`approval approval-${approval}`}
      actions={!delivered && <Badge tone={APPROVAL_TONE[approval] || 'neutral'} dot>{humanize(approval)}</Badge>}
    >
      {delivered ? (
        <Notice tone="success" title="Email delivered" />
      ) : held > 0 ? (
        <Notice tone="warning" title={held === 1 ? '1 claim on hold' : held + ' claims on hold'}>
          Resolve the held claims before sending the report.
        </Notice>
      ) : needsAttention ? (
        <Notice tone="warning" title="Review required">Check the expense review findings before approving.</Notice>
      ) : approval !== 'rejected' && !failedDelivery ? (
        <p className="approval-instruction">Approve this report to send it to finance.</p>
      ) : null}

      {!delivered && (
        <div className="approval-actions">
          <button
            type="button"
            className="btn btn-success btn-lg"
            onClick={click('approve', onApprove)}
            disabled={approvalBlocked}
          >
            {activeAction === 'approve'
              ? <Loader2 size={16} className="spin" aria-hidden="true" />
              : <Send size={16} aria-hidden="true" />}
            {activeAction === 'approve'
              ? 'Dispatching…'
              : failedDelivery ? 'Retry email delivery' : 'Approve and send'}
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

      {approvalMessage && !delivered && (
        <Notice tone={approvalMessage.type} className="approval-feedback">
          {approvalMessage.text}
        </Notice>
      )}
    </Card>
  );
}
