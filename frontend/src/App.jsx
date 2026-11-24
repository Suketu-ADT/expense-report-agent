import React, { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import { api } from './services/api';
import { ArrowRight, FileCheck2, Receipt } from 'lucide-react';
import PolicyReview from './components/PolicyReview';
import AgentPipeline from './components/AgentPipeline';
import SummaryCards from './components/SummaryCards';
import ExpenseTable from './components/ExpenseTable';
import ReviewPanel from './components/ReviewPanel';
import AgentReviewPanel from './components/AgentReviewPanel';
import ReportHistory from './components/ReportHistory';
import RunLog from './components/RunLog';
import CategoryChart from './components/CategoryChart';
import Sidebar from './components/Sidebar';
import { NAV_ITEMS } from './navigation';
import TopBar from './components/TopBar';
import RequestPanel from './components/RequestPanel';
import RunOutcome from './components/RunOutcome';
import ApprovalGate from './components/ApprovalGate';
import MemoryPanel from './components/MemoryPanel';
import { formatMonthYear } from './utils/format';
import './styles/features.css';
import './styles/workspace.css';

const SIDEBAR_KEY = 'expenseflow.sidebar.collapsed';

const DEMOS = [
  { mode: 'receipt-agents', label: 'Receipt agent demo', detail: 'Find a missing receipt and review a taxi fare discrepancy.', icon: Receipt },
  { mode: true, label: 'Two-claim jury demo', detail: 'Compare submitted expenses with the reimbursable amounts.', icon: FileCheck2 },
];

function readSection() {
  const id = window.location.hash.slice(1);
  return NAV_ITEMS.some(item => item.id === id) ? id : 'overview';
}

function readCollapsed() {
  try {
    return window.localStorage.getItem(SIDEBAR_KEY) === '1';
  } catch {
    return false;
  }
}

function App() {
  const [policyEnabled, setPolicyEnabled] = useState(false);
  const [mealCap, setMealCap] = useState('800');
  const [requestText, setRequestText] = useState("Generate my travel expense report for July 2026 and email it to finance.");
  const [runId, setRunId] = useState(null);
  const [status, setStatus] = useState("idle");
  const [runData, setRunData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [injectDiscrepancy, setInjectDiscrepancy] = useState(false);
  const [autonomyLevel, setAutonomyLevel] = useState('co_pilot');
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [approvalMessage, setApprovalMessage] = useState(null);
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [historyKey, setHistoryKey] = useState(0);

  // Presentation / feedback state (no effect on the agent workflow itself)
  const [uploadState, setUploadState] = useState(null);
  const [startError, setStartError] = useState(null);
  const [pollError, setPollError] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeSection, setActiveSection] = useState(readSection);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readCollapsed);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    let interval;
    if (runId && (status === 'running' || status === 'polling')) {
      interval = setInterval(async () => {
        try {
          const data = await api.getRunStatus(runId);
          setRunData(data);
          setPollError(false);
          if (data.status === 'completed' || data.status === 'failed') {
            setStatus(data.status);
            clearInterval(interval);
            // Refresh history after a completed run
            setHistoryKey(prev => prev + 1);
          }

          const logData = await api.getRunLogs(runId);
          setLogs(logData);
        } catch (error) {
          console.error("Polling error:", error);
          setPollError(true);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [runId, status]);

  const handleRun = async (demo = false) => {
    const resolutionDemo = demo === 'receipt-agents';
    const isDemo = demo === true || resolutionDemo;
    const cap = isDemo ? 800 : Number(mealCap);
    if (policyEnabled && (!Number.isInteger(cap) || cap <= 0 || cap > 1000000)) {
      setStartError('Enter a whole-rupee meal limit between 1 and 1,000,000.');
      return;
    }
    try {
      setStatus("running");
      setRunData(null);
      setLogs([]);
      setApprovalMessage(null);
      setStartError(null);
      setPollError(false);
      const policy = isDemo || policyEnabled ? {
        meal_cap: cap,
        demo: demo === true,
        resolution_demo: resolutionDemo,
      } : null;
      const response = await api.startRun(
        isDemo ? 'Generate July 2026 expense report' : requestText,
        !isDemo && injectDiscrepancy,
        policy,
        autonomyLevel,
      );
      setRunId(response.run_id);
    } catch (error) {
      console.error("Failed to start run:", error);
      setStartError("Failed to start the run. Check that the backend is running and reachable.");
      setPollError(false);
      setStatus("failed");
    }
  };

  const handleApprove = async () => {
    if (!runId) return;
    try {
      setApprovalLoading(true);
      const res = await api.approveReport(runId);
      setApprovalMessage({ type: 'success', text: res.message || 'Report approved and email dispatched!' });
      // Refresh status
      const updated = await api.getRunStatus(runId);
      setRunData(updated);
      setHistoryKey(prev => prev + 1);
    } catch (err) {
      console.error("Approval error:", err);
      setApprovalMessage({ type: 'error', text: 'Approval failed. Please check backend.' });
    } finally {
      setApprovalLoading(false);
    }
  };

  const handleReject = async () => {
    if (!runId) return;
    try {
      setApprovalLoading(true);
      const res = await api.rejectReport(runId);
      setApprovalMessage({ type: 'warning', text: res.message || 'Report rejected. Email delivery cancelled.' });
      const updated = await api.getRunStatus(runId);
      setRunData(updated);
    } catch (err) {
      console.error("Reject error:", err);
      setApprovalMessage({ type: 'error', text: 'Rejection failed.' });
    } finally {
      setApprovalLoading(false);
    }
  };

  // Shared by the file picker and drag-and-drop. Same API call as before; the
  // result is now shown inline instead of in a blocking alert().
  const uploadFile = async (file) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadState({ status: 'error', name: file.name, message: 'Only .csv files are supported.' });
      return;
    }

    try {
      setIsUploading(true);
      setUploadState({ status: 'uploading', name: file.name });
      await api.uploadExpenses(file);
      setUploadState({ status: 'success', name: file.name });
    } catch (error) {
      console.error("Failed to upload file:", error);
      const detail = error?.response?.data?.detail;
      setUploadState({
        status: 'error',
        name: file.name,
        message: typeof detail === 'string' ? detail : 'Failed to upload file.',
      });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleFileUpload = (event) => uploadFile(event.target.files[0]);

  // Re-fetch what is already on screen: the current run (if any) and the history.
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      if (runId) {
        const data = await api.getRunStatus(runId);
        setRunData(data);
        const logData = await api.getRunLogs(runId);
        setLogs(logData);
        setPollError(false);
      }
      setHistoryKey(prev => prev + 1);
    } catch (error) {
      console.error("Refresh error:", error);
      setPollError(true);
    } finally {
      setIsRefreshing(false);
    }
  };

  // ── Navigation ────────────────────────────────────────────────────────
  const navigateTo = useCallback((id) => {
    if (readSection() === id) {
      window.scrollTo(0, 0);
      document.getElementById('main')?.focus({ preventScroll: true });
    } else {
      window.history.pushState(null, '', '#' + id);
    }
    setActiveSection(id);
    setMobileNavOpen(false);
  }, []);

  const previousSection = useRef(activeSection);
  useLayoutEffect(() => {
    if (previousSection.current === activeSection) return;
    previousSection.current = activeSection;
    window.scrollTo(0, 0);
    document.getElementById('main')?.focus({ preventScroll: true });
  }, [activeSection]);

  useEffect(() => {
    const syncSection = () => setActiveSection(readSection());
    window.addEventListener('hashchange', syncSection);
    return () => window.removeEventListener('hashchange', syncSection);
  }, []);

  useEffect(() => {
    if (!mobileNavOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setMobileNavOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mobileNavOpen]);

  const toggleCollapsed = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(SIDEBAR_KEY, next ? '1' : '0');
      } catch {
        /* storage unavailable: the preference simply isn't remembered */
      }
      return next;
    });
  };

  // ── Derived, display-only run status (from real run state) ────────────
  const isRunning = status === 'running';
  const awaitingApproval = status === 'completed' && runData && runData.delivery_status !== 'delivered'
    && runData.approval_status !== 'rejected';
  let runStatus = { label: 'Ready', tone: 'neutral' };
  if (pollError) runStatus = { label: 'Connection issue', detail: isRunning ? 'Connection issue — retrying' : 'Connection issue', tone: 'warning' };
  else if (isRunning) runStatus = { label: 'Running', detail: runData?.current_agent ? `Running · ${runData.current_agent}` : 'Running', tone: 'info' };
  else if (status === 'failed') runStatus = { label: 'Failed', detail: 'Last run failed', tone: 'error' };
  else if (awaitingApproval) runStatus = { label: 'Awaiting approval', detail: 'Awaiting approval', tone: 'warning' };
  else if (status === 'completed') runStatus = { label: 'Completed', detail: 'Last run completed', tone: 'success' };

  const sectionLabel = NAV_ITEMS.find((n) => n.id === activeSection)?.label || 'Overview';

  const reportPeriod = formatMonthYear(runData?.date_range?.start_date);
  const hasPolicyReview = status === 'completed' && Boolean(runData?.reimbursement);

  const resumeReport = async (id) => {
    const data = await api.getRunStatus(id);
    setRunId(id);
    setRunData(data);
    setStatus(data.status);
    setApprovalMessage(null);
    setLogs(await api.getRunLogs(id));
    navigateTo('review');
  };

  return (
    <div className={`app-shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <a className="skip-link" href="#main" onClick={event => {
        event.preventDefault();
        document.getElementById('main')?.focus();
      }}>Skip to content</a>

      <Sidebar
        activeSection={activeSection}
        onNavigate={navigateTo}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={toggleCollapsed}
        mobileOpen={mobileNavOpen}
        onMobileClose={() => setMobileNavOpen(false)}
      />

      <div className="main-content">
        <TopBar
          sectionLabel={sectionLabel}
          runStatus={runStatus}
          mobileNavOpen={mobileNavOpen}
          onOpenNav={() => setMobileNavOpen(true)}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
        />

        <main id="main" className="dashboard-container" tabIndex={-1}>

          {/* Overview: request, run status, headline figures */}
          <section id="overview" className="page-section" aria-label="Overview" hidden={activeSection !== 'overview'}>
            <header className="page-header">
              <h1 className="page-title">Expense workspace</h1>
              <p className="page-subtitle">Import expenses, match receipts, and review what’s ready to reimburse.</p>
            </header>

            <div className="overview-grid">
              <RequestPanel
                requestText={requestText}
                onRequestTextChange={setRequestText}
                onRun={() => handleRun()}
                isRunning={isRunning}
                isUploading={isUploading}
                fileInputRef={fileInputRef}
                onFileInputChange={handleFileUpload}
                onDropFile={uploadFile}
                uploadState={uploadState}
                policyEnabled={policyEnabled}
                onPolicyChange={setPolicyEnabled}
                mealCap={mealCap}
                onMealCapChange={setMealCap}
                injectDiscrepancy={injectDiscrepancy}
                onInjectDiscrepancyChange={setInjectDiscrepancy}
                autonomyLevel={autonomyLevel}
                onAutonomyLevelChange={setAutonomyLevel}
              />

              <aside className="demo-card" aria-labelledby="demo-title">
                <h2 id="demo-title">Try a sample</h2>
                <p>Run a July 2026 report with sample expenses and receipts.</p>
                <div className="demo-list">
                  {DEMOS.map(({ mode, label, detail, icon: Icon }) => (
                    <button key={label} type="button" className="demo-option"
                      disabled={isRunning || isUploading} onClick={() => handleRun(mode)}>
                      <span className="demo-icon"><Icon size={19} aria-hidden="true" /></span>
                      <span className="demo-copy"><strong>{label}</strong><span>{detail}</span></span>
                      <ArrowRight size={17} className="demo-arrow" aria-hidden="true" />
                    </button>
                  ))}
                </div>
              </aside>
            </div>

            <RunOutcome
              status={status}
              runData={runData}
              startError={startError}
              pollError={pollError}
              onNavigate={navigateTo}
            />

            {(runData || isRunning) && <section className="current-report" aria-labelledby="current-report-title">
              <div className="current-report-header">
                <h2 id="current-report-title">{reportPeriod ? reportPeriod + ' summary' : 'Current report'}</h2>
                {hasPolicyReview && <button type="button" className="btn btn-secondary" onClick={() => navigateTo('review')}>
                  Review claim decisions <ArrowRight size={16} aria-hidden="true" />
                </button>}
              </div>
              <SummaryCards data={runData} isRunning={isRunning} />
            </section>}
            {activeSection === 'overview' && <ReportHistory key={historyKey} limit={3} onViewAll={() => navigateTo('history')}
              onResume={resumeReport} disabled={isRunning} />}
          </section>

          {/* Expense Reports: itemised expenses and category breakdown */}
          <section id="reports" className="page-section" aria-label="Expense reports" hidden={activeSection !== 'reports'}>
            <h1 className="page-title">Expense reports</h1>
            <div className="grid-main-side">
              <ExpenseTable data={runData} isRunning={isRunning} />
              {activeSection === 'reports' && <CategoryChart data={runData} isRunning={isRunning} />}
            </div>
          </section>

          {/* Agent Pipeline: stages and run log */}
          <section id="pipeline" className="page-section" aria-label="Agent pipeline" hidden={activeSection !== 'pipeline'}>
            <h1 className="page-title">Agent pipeline</h1>
            <AgentPipeline data={runData} logs={logs} isRunning={isRunning} />
            <RunLog logs={logs} isRunning={isRunning} />
          </section>

          {/* Review & Approvals: Unit IV review, data quality, human approval gate */}
          <section id="review" className="page-section" aria-label="Review and approvals" hidden={activeSection !== 'review'}>
            <h1 className="page-title">Review &amp; approvals</h1>
            {status === 'completed' && <PolicyReview key={runId} data={runData?.reimbursement} runId={runId}
              closed={runData?.delivery_status === 'delivered' || runData?.approval_status === 'rejected'}
                onChange={sheet => setRunData(prev => prev?.run_id === runId && sheet.revision >= prev.reimbursement?.revision
                  ? {...prev, reimbursement: sheet} : prev)}/>}
            <ApprovalGate
              data={runData}
              runStatus={status}
              approvalLoading={approvalLoading}
              approvalMessage={approvalMessage}
              onApprove={handleApprove}
              onReject={handleReject}
            />
            <div className="grid-two">
              <AgentReviewPanel data={runData} isRunning={isRunning} />
              <ReviewPanel data={runData} isRunning={isRunning} />
            </div>
          </section>

          {/* Unit III: persistent report history */}
          <section id="history" className="page-section" aria-label="Report history" hidden={activeSection !== 'history'}>
            <h1 className="page-title">Report history</h1>
            {activeSection === 'history' && <ReportHistory key={historyKey} onResume={resumeReport} disabled={isRunning} />}
          </section>

          {/* Unit III: memory recall for the current run */}
          <section id="memory" className="page-section" aria-label="Memory and insights" hidden={activeSection !== 'memory'}>
            <h1 className="page-title">Report memory</h1>
            <MemoryPanel data={runData} isRunning={isRunning} />
          </section>

        </main>
      </div>
    </div>
  );
}

export default App;
