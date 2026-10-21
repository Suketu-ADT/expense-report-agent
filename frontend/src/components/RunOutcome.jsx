import React from 'react';
import { Loader2, CheckCircle2, XCircle, CircleDashed, ArrowDown } from 'lucide-react';
import Notice from './ui/Notice';
import { formatMonthYear } from '../utils/format';

/**
 * One-line, always-present status strip for the current run (so the page does
 * not jump when a run starts). All wording about the outcome is taken from the
 * run data; the messages are the ones the app already showed on completion.
 */
export default function RunOutcome({ status, runData, startError, pollError, onNavigate }) {
  const flaggedForReview = (runData?.missing_data_flags || []).filter((f) => f.status === 'NEEDS_REVIEW').length;
  const awaitingApproval = status === 'completed' && runData && runData.delivery_status !== 'delivered';

  let tone = 'idle';
  let Icon = CircleDashed;
  let title = 'No run yet';
  let body = 'Enter a request above and run the agent to generate a report.';

  if (status === 'running') {
    tone = 'running';
    Icon = Loader2;
    title = 'Agents are running';
    body = runData?.current_agent
      ? `Current stage: ${runData.current_agent}`
      : runData?.message || 'Starting the pipeline…';
  } else if (status === 'failed') {
    tone = 'failed';
    Icon = XCircle;
    title = startError ? 'The run could not be started' : 'The run failed';
    body = null;
  } else if (status === 'completed' && runData) {
    tone = 'completed';
    Icon = CheckCircle2;
    const monthLabel = runData.date_range ? formatMonthYear(runData.date_range.start_date) : '';
    title = `Your ${monthLabel || 'expense'} report was processed.`;
    body = null;
  }

  return (
    <div className="outcome-wrap">
      <div className={`outcome outcome-${tone}`} aria-live="polite">
        <span className="outcome-icon" aria-hidden="true">
          <Icon size={18} className={tone === 'running' ? 'spin' : ''} />
        </span>
        <div className="outcome-main">
          <div className="outcome-title">{title}</div>

          {body && <div className="outcome-text">{body}</div>}

          {tone === 'completed' && (
            <ul className="outcome-lines">
              {runData.delivery_status === 'delivered' && <li>Report generated successfully. Email delivery was successful.</li>}
              {runData.delivery_status === 'failed' && <li>Report generated successfully. Email delivery failed.</li>}
              {runData.delivery_status === 'pending' && runData.needs_human_review && (
                <li className="text-warning">Email dispatch held: Requires human review before sending.</li>
              )}
              {runData.delivery_status === 'pending' && !runData.needs_human_review && (
                <li>Pipeline finished. Email delivery pending.</li>
              )}
              {flaggedForReview > 0 && <li>{flaggedForReview} item(s) require review.</li>}
              {runData.report_id && (
                <li>Persisted in SQLite memory as <strong className="mono">{runData.report_id}</strong></li>
              )}
            </ul>
          )}

          {tone === 'failed' && (
            <ul className="outcome-lines">
              {startError && <li>{startError}</li>}
              {(runData?.errors || []).map((e, i) => <li key={i}>{e}</li>)}
              {!startError && !(runData?.errors || []).length && (
                <li>The backend did not return an error message. Check the run log for details.</li>
              )}
            </ul>
          )}
        </div>

        {awaitingApproval && (
          <button type="button" className="btn btn-secondary btn-sm outcome-cta" onClick={() => onNavigate('review')}>
            <ArrowDown size={14} aria-hidden="true" />
            Go to approval
          </button>
        )}
      </div>

      {pollError && (
        <Notice tone="warning" title="Live status is temporarily unavailable">
          The last request to the backend failed.
          {status === 'running' ? ' The app keeps retrying automatically.' : ' Use Refresh to try again.'}
        </Notice>
      )}
    </div>
  );
}
