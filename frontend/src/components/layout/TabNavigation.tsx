// Tab Navigation Component
// Terminal-style tabs for switching between dashboard views

import { 
  FileText, 
  FlaskConical, 
  Cpu, 
  Sparkles, 
  FolderGit2, 
  Activity, 
  Network 
} from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { useDashboard } from '@/hooks/useDashboard';
import type { TabName } from '@/types';

interface TabConfig {
  value: TabName;
  label: string;
  icon: React.ReactNode;
  badge?: number;
}

export function TabNavigation() {
  const { currentTab, setTab, stats } = useDashboard();

  const tabs: TabConfig[] = [
    {
      value: 'proposals',
      label: 'Proposals',
      icon: <FileText className="w-4 h-4" />,
      badge: stats.pendingProposals > 0 ? stats.pendingProposals : undefined,
    },
    {
      value: 'experiments',
      label: 'Experiments',
      icon: <FlaskConical className="w-4 h-4" />,
    },
    {
      value: 'workers',
      label: 'Workers',
      icon: <Cpu className="w-4 h-4" />,
    },
    {
      value: 'patterns',
      label: 'Patterns',
      icon: <Sparkles className="w-4 h-4" />,
    },
    {
      value: 'projects',
      label: 'Projects',
      icon: <FolderGit2 className="w-4 h-4" />,
    },
    {
      value: 'logs',
      label: 'Live Logs',
      icon: <Activity className="w-4 h-4" />,
    },
    {
      value: 'graph',
      label: 'Graph',
      icon: <Network className="w-4 h-4" />,
    },
  ];

  return (
    <Tabs value={currentTab} onValueChange={(value) => setTab(value as TabName)} className="mb-6">
      <TabsList className="terminal-border bg-background-secondary border-gray-800 p-1 h-auto flex-wrap justify-start">
        {tabs.map((tab) => (
          <TabsTrigger
            key={tab.value}
            value={tab.value}
            className="terminal-border font-mono text-sm data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-primary data-[state=active]:glow-text transition-all"
          >
            <span className="flex items-center gap-2">
              {tab.icon}
              {tab.label}
              {tab.badge !== undefined && (
                <Badge 
                  variant="outline" 
                  className="ml-1 bg-terminal-yellow/20 text-terminal-yellow border-terminal-yellow text-xs"
                >
                  {tab.badge}
                </Badge>
              )}
            </span>
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
