import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { History, RefreshCw, ChevronDown, Loader2, Inbox, FileDown } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import Notice from './ui/Notice';
import EmptyState from './ui/EmptyState';
import { formatMoney, formatDate, formatDateTime, humanize } from '../utils/format';
import { exportReportHistoryPdf } from '../utils/exportHistoryPdf';

const REVIEW_TONE = { passed: 'success', needs_correction: 'warning', needs_human_review: 'error' };
const REVIEW_LABEL = {
  passed: 'Review passed',
  needs_correction: 'Correction required',
  needs_human_review: 'Human review',
};

export default function ReportHistory() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loadingId, setLoadingId] = useState(null);
  const [detailError, setDetailError] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await api.getReportHistory();
      setReports(data.reports || []);
      setError(null);
    } catch (err) {
      setError("Failed to load report history");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleExport = async () => {
    try {
      setExporting(true);
      setExportError(null);
      await exportReportHistoryPdf(reports);
    } catch (err) {
      console.error("Failed to export report history:", err);
      setExportError("Could not create the PDF. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const handleViewReport = async (reportId) => {
    // Collapsing needs no request; expanding retrieves the saved report.
    if (expandedId === reportId) {
      setExpandedId(null);
      return;
    }
    try {
      setLoadingId(reportId);
      setDetailError(null);
      const data = await api.getSavedReport(reportId);
      setSelectedReport(data);
      setExpandedId(reportId);
    } catch (err) {
      console.error("Failed to load report:", err);
      setDetailError({ id: reportId, text: `Could not load report ${reportId}.` });
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <Card
      id="history-card"
      title="Report history"
      description="Reports saved to persistent memory (SQLite). Select a report to load its saved details."
      icon={History}
      flush
      actions={
        <>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleExport}
            disabled={loading || exporting || reports.length === 0}
            title={reports.length === 0 ? 'No reports to export' : 'Download the report history as a PDF'}
          >
            {exporting ? <Loader2 size={14} className="spin" aria-hidden="true" /> : <FileDown size={14} aria-hidden="true" />}
            {exporting ? 'Preparing PDF…' : 'Export PDF'}
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={fetchHistory} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} aria-hidden="true" />
            Refresh history
          </button>
        </>
      }
    >
      {exportError && (
        <div className="card-pad"><Notice tone="error">{exportError}</Notice></div>
      )}

      {loading && reports.length === 0 && (
        <div className="history-skeleton" aria-busy="true" aria-label="Loading report history">
          {[0, 1, 2].map((i) => <span key={i} className="skeleton skeleton-row" />)}
        </div>
      )}

      {error && (
        <div className="card-pad">
          <Notice tone="error" title={error}>
            The backend could not be reached or returned an error. Use “Refresh history” to try again.
          </Notice>
        </div>
      )}

      {!loading && !error && reports.length === 0 && (
        <EmptyState icon={Inbox} title="No previous reports">
          Run the agent to generate your first report. It will be saved here automatically.
        </EmptyState>
      )}

      {reports.length > 0 && (
        <div className="history">
          <div className="history-cols" aria-hidden="true">
            <span>Report</span>
            <span>Period</span>
            <span className="num">Final amount</span>
            <span>Review status</span>
            <span>Created</span>
            <span />
          </div>
          <ul className="history-list">
            {reports.map((report) => {
              const open = expandedId === report.report_id;
              const busy = loadingId === report.report_id;
              return (
                <li key={report.report_id} className={`history-item ${open ? 'open' : ''}`}>
                  <button
                    type="button"
                    className="history-row"
                    onClick={() => handleViewReport(report.report_id)}
                    aria-expanded={open}
                    aria-controls={`report-${report.report_id}`}
                    disabled={busy}
                  >
                    <span className="mono history-id" data-label="Report">{report.report_id}</span>
                    <span data-label="Period">{report.period_label}</span>
                    <span className="num history-amount" data-label="Final amount">{formatMoney(report.confirmed_total)}</span>
                    <span data-label="Review status">
                      <Badge tone={REVIEW_TONE[report.review_status] || 'neutral'}>
                        {REVIEW_LABEL[report.review_status] || humanize(report.review_status) || 'Pending'}
                      </Badge>
                    </span>
                    <span className="history-date" data-label="Created">{report.created_at ? formatDate(report.created_at) : '—'}</span>
                    <span className="history-chevron" aria-hidden="true">
                      {busy ? <Loader2 size={15} className="spin" /> : <ChevronDown size={15} className={open ? 'flip' : ''} />}
                    </span>
                  </button>

                  {detailError?.id === report.report_id && (
                    <div className="card-pad"><Notice tone="error">{detailError.text}</Notice></div>
                  )}

                  {open && selectedReport && (
                    <div id={`report-${report.report_id}`} className="history-detail">
                      <dl className="detail-grid">
                        <div><dt>Confirmed total</dt><dd className="num text-success">{formatMoney(selectedReport.confirmed_total)}</dd></div>
                        <div><dt>Provisional total</dt><dd className="num text-warning">{formatMoney(selectedReport.provisional_total)}</dd></div>
                        <div><dt>Total expenses</dt><dd className="num">{selectedReport.total_expenses}</dd></div>
                        <div><dt>Flagged</dt><dd className="num">{selectedReport.flagged_count}</dd></div>
                        <div><dt>Excluded</dt><dd className="num">{selectedReport.excluded_count}</dd></div>
                        <div><dt>Delivery</dt><dd>{humanize(selectedReport.delivery_status)}</dd></div>
                        <div><dt>Period</dt><dd>{selectedReport.period_start} → {selectedReport.period_end}</dd></div>
                        <div><dt>Run ID</dt><dd className="mono" title={selectedReport.run_id}>{selectedReport.run_id?.slice(0, 8)}…</dd></div>
                        <div><dt>Saved</dt><dd>{formatDateTime(selectedReport.created_at)}</dd></div>
                      </dl>

                      {selectedReport.category_totals && Object.keys(selectedReport.category_totals).length > 0 && (
                        <div className="detail-block">
                          <h4 className="subhead">Category breakdown</h4>
                          <ul className="kv-list">
                            {Object.entries(selectedReport.category_totals).map(([cat, val]) => (
                              <li key={cat}><span>{cat}</span><span className="num">{formatMoney(val)}</span></li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {selectedReport.review_findings && selectedReport.review_findings.length > 0 && (
                        <div className="detail-block">
                          <h4 className="subhead">Review findings</h4>
                          <ul className="finding-list">
                            {selectedReport.review_findings.map((f, i) => (
                              <li key={i} className={`finding finding-${f.severity === 'critical' ? 'error' : 'warning'}`}>
                                <div className="finding-head">
                                  <span className="finding-type">{humanize(f.finding_type)}</span>
                                  <Badge tone={f.resolution_status === 'resolved' ? 'success' : 'warning'}>{humanize(f.resolution_status)}</Badge>
                                </div>
                                <p className="finding-desc">{f.description}</p>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Card>
  );
}
