import React, { useState } from 'react';
import { Play, Upload, Bug, FileSpreadsheet, Loader2, CheckCircle2, XCircle, ChevronDown, ShieldCheck } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';

const AUTONOMY_LEVELS = [
  { value: 'cautious', label: 'Cautious', hint: '0 auto-retries — any finding, even a warning, goes to a human.' },
  { value: 'co_pilot', label: 'Co-pilot', hint: 'Default — up to 3 auto-correction retries before escalating.' },
  { value: 'trusting', label: 'Trusting', hint: 'Up to 5 auto-correction retries before escalating.' },
];

/**
 * Report request form. All state and handlers are owned by App and passed in;
 * this component only decides how they are presented.
 */
export default function RequestPanel({
  requestText,
  onRequestTextChange,
  onRun,
  isRunning,
  isUploading,
  fileInputRef,
  onFileInputChange,
  onDropFile,
  uploadState,
  policyEnabled,
  onPolicyChange,
  mealCap,
  onMealCapChange,
  injectDiscrepancy,
  onInjectDiscrepancyChange,
  autonomyLevel,
  onAutonomyLevelChange,
}) {
  const [dragging, setDragging] = useState(false);
  const busy = isRunning || isUploading;

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (busy) return;
    const file = e.dataTransfer?.files?.[0];
    if (file) onDropFile(file);
  };

  return (
    <Card
      id="request"
      title="New report"
      className="request-card"
    >
      <div className="request-grid">
        <div className="field">
          <label className="field-label" htmlFor="request-text">Request</label>
          <textarea
            id="request-text"
            className="textarea"
            rows={3}
            value={requestText}
            onChange={(e) => onRequestTextChange(e.target.value)}
            disabled={busy}
            placeholder="e.g. Generate my travel expense report for July 2026 and email it to finance."
          />
        </div>

        <div className="field">
          <span className="field-label" id="upload-label">Expense data (CSV)</span>
          <input
            type="file"
            accept=".csv"
            className="visually-hidden"
            ref={fileInputRef}
            onChange={onFileInputChange}
            tabIndex={-1}
            aria-hidden="true"
          />
          <button
            type="button"
            className={`dropzone ${dragging ? 'dragging' : ''} ${uploadState?.status ? `dropzone-${uploadState.status}` : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); if (!busy) setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            disabled={busy}
            aria-labelledby="upload-label"
          >
            <span className="dropzone-icon" aria-hidden="true">
              {isUploading ? <Loader2 size={18} className="spin" />
                : uploadState?.status === 'success' ? <CheckCircle2 size={18} />
                : uploadState?.status === 'error' ? <XCircle size={18} />
                : <FileSpreadsheet size={18} />}
            </span>
            <span className="dropzone-text">
              {isUploading ? (
                <>
                  <span className="dropzone-title">Uploading {uploadState?.name || 'file'}…</span>
                  <span className="dropzone-sub">Please wait</span>
                </>
              ) : uploadState?.status === 'success' ? (
                <>
                  <span className="dropzone-title">{uploadState.name}</span>
                  <span className="dropzone-sub">Uploaded. Click to replace.</span>
                </>
              ) : uploadState?.status === 'error' ? (
                <>
                  <span className="dropzone-title">{uploadState.name || 'Upload failed'}</span>
                  <span className="dropzone-sub">{uploadState.message} Click to try again.</span>
                </>
              ) : (
                <>
                  <span className="dropzone-title">Upload CSV</span>
                  <span className="dropzone-sub">Choose a file or drop it here</span>
                </>
              )}
            </span>
            <Upload size={15} className="dropzone-trailing" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="policy-setup">
        <label className="policy-toggle">
          <input type="checkbox" className="checkbox" checked={policyEnabled}
            onChange={event => onPolicyChange(event.target.checked)} disabled={busy} />
          <span>
            <strong>Apply reimbursement policy</strong>
            <small>Match receipts and calculate eligible amounts.</small>
          </span>
        </label>
        {policyEnabled && <label className="meal-limit">
          Meal limit (INR)
          <input type="number" min="1" max="1000000" step="1" value={mealCap}
            onChange={event => onMealCapChange(event.target.value)} disabled={busy} />
        </label>}
      </div>

      <div className="request-footer">
      <details className="advanced">
        <summary className="advanced-summary">
          <ChevronDown size={14} className="advanced-chevron" aria-hidden="true" />
          <span>Advanced</span>
          {injectDiscrepancy && <Badge tone="warning" icon={Bug}>Discrepancy on</Badge>}
          {autonomyLevel !== 'co_pilot' && (
            <Badge tone={autonomyLevel === 'cautious' ? 'neutral' : 'warning'} icon={ShieldCheck}>
              {AUTONOMY_LEVELS.find((l) => l.value === autonomyLevel)?.label}
            </Badge>
          )}
        </summary>
        <label className="check-row">
          <input
            type="checkbox"
            className="checkbox"
            checked={injectDiscrepancy}
            onChange={(e) => onInjectDiscrepancyChange(e.target.checked)}
            disabled={isRunning}
          />
          <span className="check-text">
            <span className="check-title"><Bug size={13} aria-hidden="true" /> Inject a calculation discrepancy</span>
            <span className="check-sub">
              Adds a deliberate error to test the review and correction loop.
            </span>
          </span>
        </label>
        <div className="field">
          <label className="field-label" htmlFor="autonomy-level">
            <ShieldCheck size={13} aria-hidden="true" /> Autonomy level
          </label>
          <select
            id="autonomy-level"
            className="select"
            value={autonomyLevel}
            onChange={(e) => onAutonomyLevelChange(e.target.value)}
            disabled={isRunning}
          >
            {AUTONOMY_LEVELS.map((level) => (
              <option key={level.value} value={level.value}>{level.label}</option>
            ))}
          </select>
          <small className="check-sub">
            {AUTONOMY_LEVELS.find((l) => l.value === autonomyLevel)?.hint}
            {' '}Email dispatch always needs your explicit approval regardless of level.
          </small>
        </div>
      </details>

      <div className="request-actions">
        <button
          type="button"
          className="btn btn-primary btn-lg"
          onClick={onRun}
          disabled={busy}
        >
          {isRunning ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
          {isRunning ? 'Running…' : 'Generate report'}
        </button>
      </div>
      </div>
    </Card>
  );
}
