import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from './services/api';
import { Play, Loader2 } from 'lucide-react';
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
import './index.css';
import './styles/features.css';

const SIDEBAR_KEY = 'expenseflow.sidebar.collapsed';

function readCollapsed() {
  try {
    return window.localStorage.getItem(SIDEBAR_KEY) === '1';
  } catch {
    return false;
  }
}

function App() {
  const [requestText, setRequestText] = useState("Generate my travel expense report for July 2026 and email it to finance.");
  const [runId, setRunId] = useState(null);
  const [status, setStatus] = useState("idle");
  const [runData, setRunData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [injectDiscrepancy, setInjectDiscrepancy] = useState(false);
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
  const [activeSection, setActiveSection] = useState('overview');
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

  const handleRun = async () => {
    try {
      setStatus("running");
      setRunData(null);
      setLogs([]);
      setApprovalMessage(null);
      setStartError(null);
      setPollError(false);
      const response = await api.startRun(requestText, injectDiscrepancy);
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
    const el = document.getElementById(id);
    if (!el) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    setActiveSection(id);
    setMobileNavOpen(false);
  }, []);

  // Scroll-spy: the active item is the last section whose top has passed the header.
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
      let current = NAV_ITEMS[0].id;
      if (atBottom) {
        current = NAV_ITEMS[NAV_ITEMS.length - 1].id;
      } else {
        for (const item of NAV_ITEMS) {
          const el = document.getElementById(item.id);
          if (el && el.getBoundingClientRect().top <= 120) current = item.id;
        }
      }
      setActiveSection(current);
    };
    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(update);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    update();
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      if (frame) window.cancelAnimationFrame(frame);
    };
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
  let runStatus = { label: 'Idle', detail: 'No run in progress', tone: 'neutral' };
  if (pollError) runStatus = { label: 'Connection issue', detail: isRunning ? 'Connection issue — retrying' : 'Connection issue', tone: 'warning' };
  else if (isRunning) runStatus = { label: 'Running', detail: runData?.current_agent ? `Running · ${runData.current_agent}` : 'Running', tone: 'info' };
  else if (status === 'failed') runStatus = { label: 'Failed', detail: 'Last run failed', tone: 'error' };
  else if (awaitingApproval) runStatus = { label: 'Awaiting approval', detail: 'Awaiting approval', tone: 'warning' };
  else if (status === 'completed') runStatus = { label: 'Completed', detail: 'Last run completed', tone: 'success' };

  const sectionLabel = NAV_ITEMS.find((n) => n.id === activeSection)?.label || 'Overview';

  return (
    <div className={`app-shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <a className="skip-link" href="#main">Skip to content</a>

      <Sidebar
        activeSection={activeSection}
        onNavigate={navigateTo}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={toggleCollapsed}
        mobileOpen={mobileNavOpen}
        onMobileClose={() => setMobileNavOpen(false)}
        runStatus={runStatus}
      />

      <div className="main-content">
        <TopBar
          sectionLabel={sectionLabel}
          runStatus={runStatus}
          onOpenNav={() => setMobileNavOpen(true)}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
        />

        <main id="main" className="dashboard-container">

          {/* Overview: request, run status, headline figures */}
          <section id="overview" className="page-section" aria-label="Overview">
            <div className="page-header">
              <div>
                <h1 className="page-title">Expense Intelligence</h1>
                <p className="page-subtitle">
                  Automate expense reporting, validate transactions, and review AI-generated financial summaries.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleRun}
                disabled={isRunning || isUploading}
              >
                {isRunning ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
                {isRunning ? 'Running…' : 'Generate Report'}
              </button>
            </div>

            <RequestPanel
              requestText={requestText}
              onRequestTextChange={setRequestText}
              onRun={handleRun}
              isRunning={isRunning}
              isUploading={isUploading}
              fileInputRef={fileInputRef}
              onFileInputChange={handleFileUpload}
              onDropFile={uploadFile}
              uploadState={uploadState}
              injectDiscrepancy={injectDiscrepancy}
              onInjectDiscrepancyChange={setInjectDiscrepancy}
            />

            <RunOutcome
              status={status}
              runData={runData}
              startError={startError}
              pollError={pollError}
              onNavigate={navigateTo}
            />

            <SummaryCards data={runData} isRunning={isRunning} />
          </section>

          {/* Expense Reports: itemised expenses and category breakdown */}
          <section id="reports" className="page-section" aria-label="Expense reports">
            <h2 className="section-title">Expense Reports</h2>
            <div className="grid-main-side">
              <ExpenseTable data={runData} isRunning={isRunning} />
              <CategoryChart data={runData} isRunning={isRunning} />
            </div>
          </section>

          {/* Agent Pipeline: stages and run log */}
          <section id="pipeline" className="page-section" aria-label="Agent pipeline">
            <h2 className="section-title">Agent Pipeline</h2>
            <AgentPipeline data={runData} logs={logs} isRunning={isRunning} />
            <RunLog logs={logs} isRunning={isRunning} />
          </section>

          {/* Review & Approvals: Unit IV review, data quality, human approval gate */}
          <section id="review" className="page-section" aria-label="Review and approvals">
            <h2 className="section-title">Review &amp; Approvals</h2>
            <ApprovalGate
              data={runData}
              runStatus={status}
              logs={logs}
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
          <section id="history" className="page-section" aria-label="Report history">
            <h2 className="section-title">Report History</h2>
            <ReportHistory key={historyKey} />
          </section>

          {/* Unit III: memory recall for the current run */}
          <section id="memory" className="page-section" aria-label="Memory and insights">
            <h2 className="section-title">Memory &amp; Insights</h2>
            <MemoryPanel data={runData} isRunning={isRunning} />
          </section>

        </main>
      </div>
    </div>
  );
}

export default App;
