import { LayoutDashboard, FileText, Workflow, ShieldCheck, History, Archive } from 'lucide-react';

// Every item maps to a real section id rendered on the page (see App.jsx).
export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'review', label: 'Review & approvals', icon: ShieldCheck },
  { id: 'reports', label: 'Expense reports', icon: FileText },
  { id: 'history', label: 'Report history', icon: History },
  { id: 'pipeline', label: 'Agent pipeline', icon: Workflow },
  { id: 'memory', label: 'Report memory', icon: Archive },
];
