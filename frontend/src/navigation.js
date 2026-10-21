import { LayoutDashboard, FileText, Workflow, ShieldCheck, History, Brain } from 'lucide-react';

// Every item maps to a real section id rendered on the page (see App.jsx).
export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'reports', label: 'Expense Reports', icon: FileText },
  { id: 'pipeline', label: 'Agent Pipeline', icon: Workflow },
  { id: 'review', label: 'Review & Approvals', icon: ShieldCheck },
  { id: 'history', label: 'Report History', icon: History },
  { id: 'memory', label: 'Memory & Insights', icon: Brain },
];
