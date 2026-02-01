// SIGMA Agent Dashboard - Main App Component

import { useDashboardInit, useCurrentTab, useToasts, useDashboard } from '@/hooks/useDashboard';
import { Header } from '@/components/layout/Header';
import { StatsGrid } from '@/components/layout/StatsGrid';
import { TabNavigation } from '@/components/layout/TabNavigation';
import { ProposalsTab } from '@/components/features/ProposalsTab';
import { WorkersTab } from '@/components/features/WorkersTab';
import { ProjectsTab } from '@/components/features/ProjectsTab';
import { ExperimentsTab } from '@/components/features/ExperimentsTab';
import { PatternsTab } from '@/components/features/PatternsTab';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

// Placeholder components for remaining tabs (will be implemented in Phase 4)

function LogsTab() {
  return (
    <div className="terminal-card bg-background-secondary p-8 text-center">
      <p className="text-gray-400 font-mono">Live Logs tab - Coming in Phase 4</p>
    </div>
  );
}

function GraphTab() {
  return (
    <div className="terminal-card bg-background-secondary p-8 text-center">
      <p className="text-gray-400 font-mono">Graph visualization - Coming in Phase 4</p>
    </div>
  );
}

// Toast notification component
function ToastContainer() {
  const toasts = useToasts();
  const { removeToast } = useDashboard();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            'terminal-border p-4 pr-10 rounded font-mono text-sm shadow-lg animate-slideDown relative',
            toast.type === 'success' && 'bg-terminal-green/20 border-terminal-green text-terminal-green',
            toast.type === 'error' && 'bg-terminal-red/20 border-terminal-red text-terminal-red',
            toast.type === 'warning' && 'bg-terminal-yellow/20 border-terminal-yellow text-terminal-yellow',
            toast.type === 'info' && 'bg-primary/20 border-primary text-primary'
          )}
        >
          {toast.message}
          <button
            onClick={() => removeToast(toast.id)}
            className="absolute top-2 right-2 hover:opacity-70"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}

// Main App
function App() {
  // Initialize dashboard (loads data, sets up auto-refresh, keyboard shortcuts)
  useDashboardInit();
  
  const currentTab = useCurrentTab();

  return (
    <div className="min-h-screen bg-background text-gray-100 p-6">
      <div className="max-w-[1600px] mx-auto">
        {/* Header */}
        <Header />

        {/* Stats Grid */}
        <StatsGrid />

        {/* Tab Navigation */}
        <TabNavigation />

        {/* Tab Content */}
        <div className="tab-content">
          {currentTab === 'proposals' && <ProposalsTab />}
          {currentTab === 'experiments' && <ExperimentsTab />}
          {currentTab === 'workers' && <WorkersTab />}
          {currentTab === 'patterns' && <PatternsTab />}
          {currentTab === 'projects' && <ProjectsTab />}
          {currentTab === 'logs' && <LogsTab />}
          {currentTab === 'graph' && <GraphTab />}
        </div>

        {/* Toast Notifications */}
        <ToastContainer />
      </div>
    </div>
  );
}

export default App;
