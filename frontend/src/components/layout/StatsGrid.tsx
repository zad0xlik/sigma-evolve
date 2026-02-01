// Dashboard Stats Grid Component
// Displays 4 key metrics in terminal-style cards

import { FolderGit2, FileText, TrendingUp, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useDashboardStats } from '@/hooks/useDashboard';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
}

function StatCard({ title, value, icon, color }: StatCardProps) {
  return (
    <Card className="terminal-card bg-background-secondary border-gray-800 hover:border-primary/50 transition-colors">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-mono text-gray-400 uppercase tracking-wide">
          {title}
        </CardTitle>
        <div className={`text-${color}`}>{icon}</div>
      </CardHeader>
      <CardContent>
        <div className={`text-3xl font-bold font-mono text-${color} glow-text`}>
          {value}
        </div>
      </CardContent>
    </Card>
  );
}

export function StatsGrid() {
  const stats = useDashboardStats();

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <StatCard
        title="Projects"
        value={stats.totalProjects}
        icon={<FolderGit2 className="w-5 h-5" />}
        color="terminal-blue"
      />
      
      <StatCard
        title="Pending Proposals"
        value={stats.pendingProposals}
        icon={<FileText className="w-5 h-5" />}
        color="terminal-yellow"
      />
      
      <StatCard
        title="Success Rate"
        value={stats.successRate}
        icon={<TrendingUp className="w-5 h-5" />}
        color="terminal-green"
      />
      
      <StatCard
        title="Patterns Learned"
        value={stats.totalPatterns}
        icon={<Sparkles className="w-5 h-5" />}
        color="terminal-purple"
      />
    </div>
  );
}
