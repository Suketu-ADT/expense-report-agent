import React, { useState } from 'react';
import { Play, Upload, Bug, FileSpreadsheet, Loader2, CheckCircle2, XCircle, ChevronDown } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';

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
  injectDiscrepancy,
  onInjectDiscrepancyChange,
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
      title="Report request"
      description="Describe the report you need. The agents will retrieve, validate, categorise and review the expenses."
      icon={Play}
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
                  <span className="dropzone-sub">Uploaded — ready to run. Click to replace.</span>
                </>
              ) : uploadState?.status === 'error' ? (
                <>
                  <span className="dropzone-title">{uploadState.name || 'Upload failed'}</span>
                  <span className="dropzone-sub">{uploadState.message} Click to try again.</span>
                </>
              ) : (
                <>
                  <span className="dropzone-title">Drop a CSV here or <u>browse</u></span>
                  <span className="dropzone-sub">Replaces the expense data used by the next run.</span>
                </>
              )}
            </span>
            <Upload size={15} className="dropzone-trailing" aria-hidden="true" />
          </button>
        </div>
      </div>

      <details className="advanced">
        <summary className="advanced-summary">
          <ChevronDown size={14} className="advanced-chevron" aria-hidden="true" />
          <span>Advanced · demonstration settings</span>
          {injectDiscrepancy && <Badge tone="warning" icon={Bug}>Discrepancy injection on</Badge>}
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
            <span className="check-title"><Bug size={13} aria-hidden="true" /> Unit IV demo: inject calculation discrepancy</span>
            <span className="check-sub">
              Test feature. Adds a deliberate error to the confirmed total so you can watch the Review Agent detect it and trigger the correction loop. Leave off for normal reports.
            </span>
          </span>
        </label>
      </details>

      <div className="request-actions">
        <button
          type="button"
          className="btn btn-primary btn-lg"
          onClick={onRun}
          disabled={busy}
        >
          {isRunning ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
          {isRunning ? 'Running agents…' : 'Run Agent'}
        </button>
      </div>
    </Card>
  );
}
