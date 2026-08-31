import React from 'react';
import { Settings, Database, Filter, Tag, Calculator, FileText, Send } from 'lucide-react';

const AGENTS = [
  { name: 'Orchestrator', icon: Settings },
  { name: 'Data Retrieval', icon: Database },
  { name: 'Filter & Validation', icon: Filter },
  { name: 'Categorization', icon: Tag },
  { name: 'Calculation', icon: Calculator },
  { name: 'Report Generation', icon: FileText },
  { name: 'Email Dispatch', icon: Send },
];

export default function AgentPipeline({ data }) {
  const getStatus = (agentName) => {
    if (!data || !data.agent_status) return 'waiting';
    return data.agent_status[agentName]?.toLowerCase() || 'waiting';
  };

  return (
    <div>
      <h3 style={{ marginTop: 0, marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>AGENT PIPELINE</h3>
      <div className="pipeline-container">
        {AGENTS.map((agent, index) => {
          const status = getStatus(agent.name);
          const Icon = agent.icon;
          
          return (
            <div key={index} className={`agent-card ${status}`}>
              <div className="agent-icon">
                <Icon size={20} />
              </div>
              <span className="agent-name">{agent.name}</span>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                {status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
