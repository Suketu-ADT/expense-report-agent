import React, { useState, useEffect, useRef } from 'react';
import { api } from './services/api';
import { Play, Upload } from 'lucide-react';
import AgentPipeline from './components/AgentPipeline';
import SummaryCards from './components/SummaryCards';
import ExpenseTable from './components/ExpenseTable';
import ReviewPanel from './components/ReviewPanel';
import RunLog from './components/RunLog';
import CategoryChart from './components/CategoryChart';
import './index.css';

function App() {
  const [requestText, setRequestText] = useState("Generate my travel expense report for last month and email it to finance.");
  const [runId, setRunId] = useState(null);
  const [status, setStatus] = useState("idle");
  const [runData, setRunData] = useState(null);
  const [logs, setLogs] = useState([]);
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    let interval;
    if (runId && (status === 'running' || status === 'polling')) {
      interval = setInterval(async () => {
        try {
          const data = await api.getRunStatus(runId);
          setRunData(data);
          if (data.status === 'completed' || data.status === 'failed') {
            setStatus(data.status);
            clearInterval(interval);
          }
          
          const logData = await api.getRunLogs(runId);
          setLogs(logData);
        } catch (error) {
          console.error("Polling error:", error);
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
      const response = await api.startRun(requestText);
      setRunId(response.run_id);
    } catch (error) {
      console.error("Failed to start run:", error);
      setStatus("failed");
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
      setIsUploading(true);
      await api.uploadExpenses(file);
      alert("Expenses uploaded successfully! You can now run the agent.");
    } catch (error) {
      console.error("Failed to upload file:", error);
      alert("Failed to upload file.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1>EXPENSE REPORT AGENT</h1>
        <p>Autonomous travel expense reporting powered by multi-agent AI</p>
      </header>

      <section className="panel">
        <div className="input-section">
          <input 
            type="text" 
            className="prompt-input" 
            value={requestText}
            onChange={(e) => setRequestText(e.target.value)}
            disabled={status === 'running' || isUploading}
          />
          <input 
            type="file" 
            accept=".csv" 
            style={{ display: 'none' }} 
            ref={fileInputRef}
            onChange={handleFileUpload}
          />
          <button 
            className="upload-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={status === 'running' || isUploading}
          >
            <Upload size={20} />
            {isUploading ? "Uploading..." : "Upload CSV"}
          </button>
          <button 
            className="run-btn" 
            onClick={handleRun}
            disabled={status === 'running' || isUploading}
          >
            <Play size={20} />
            Run Agent
          </button>
        </div>
      </section>

      {(runId || status === 'running') && (
        <section className="panel">
          <AgentPipeline data={runData} />
        </section>
      )}

      {status === 'completed' && runData && (
        <div className="final-message">
          Your July 2026 expense report was generated successfully.
          <br/>Report generated successfully. Email delivery was simulated because DEVELOPMENT_MODE is enabled.
          {runData.missing_data_flags && runData.missing_data_flags.filter(f => f.status === 'NEEDS_REVIEW').length > 0 && (
            <><br/>{runData.missing_data_flags.filter(f => f.status === 'NEEDS_REVIEW').length} item requires your review.</>
          )}
        </div>
      )}

      {runData && (
        <>
          <section className="dashboard-grid">
            <SummaryCards data={runData} />
          </section>

          <div className="content-grid">
            <div className="main-col">
              <section className="panel">
                <ExpenseTable data={runData} />
              </section>
              
              <section className="panel">
                <RunLog logs={logs} />
              </section>
            </div>
            
            <div className="side-col">
              <section className="panel">
                <CategoryChart data={runData} />
              </section>
              
              <section className="panel">
                <ReviewPanel data={runData} />
              </section>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
