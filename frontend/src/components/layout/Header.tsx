// Dashboard Header Component
// Terminal-style header with title, stats, and controls

import { RefreshCw, Power, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useDashboard } from '@/hooks/useDashboard';
import { cn } from '@/lib/utils';

export function Header() {
  const { lastUpdate, loading, autoRefresh, refreshData, setAutoRefresh } = useDashboard();

  return (
    <header className="terminal-border bg-background-secondary p-4 mb-6">
      <div className="flex items-center justify-between">
        {/* Title */}
        <div>
          <h1 className="text-2xl font-bold text-primary glow-text font-mono">
            SIGMA AGENT DASHBOARD
          </h1>
          <p className="text-sm text-gray-400 mt-1 font-mono">
            Self-Improving Multi-Agent System
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-4">
          {/* Last Update */}
          {lastUpdate && (
            <div className="text-sm text-gray-400 font-mono">
              Last update: <span className="text-terminal-green">{lastUpdate}</span>
            </div>
          )}

          {/* Auto-refresh toggle */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={cn(
              'terminal-border font-mono',
              autoRefresh
                ? 'bg-terminal-green/10 text-terminal-green border-terminal-green'
                : 'bg-background text-gray-400'
            )}
          >
            <Zap className="w-4 h-4 mr-2" />
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </Button>

          {/* Refresh button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => refreshData()}
            disabled={loading}
            className="terminal-border font-mono text-primary hover:text-primary hover:bg-primary/10"
          >
            <RefreshCw className={cn('w-4 h-4 mr-2', loading && 'animate-spin')} />
            Refresh
          </Button>

          {/* System status indicator */}
          <div className="flex items-center gap-2 text-terminal-green font-mono text-sm">
            <Power className="w-4 h-4" />
            <span>ONLINE</span>
          </div>
        </div>
      </div>
    </header>
  );
}
