import { useState } from 'react';
import { Cpu, Play, Activity, CheckCircle2, XCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDashboard } from '@/hooks/useDashboard';
import type { WorkerStats, WorkerStartRequest } from '@/types';
import { format } from 'date-fns';

const WORKER_TYPES = [
  { value: 'analysis', label: 'Analysis Worker', description: 'Code parsing, metrics, issue detection' },
  { value: 'dream', label: 'Dream Worker', description: 'Knowledge graph relationships' },
  { value: 'recall', label: 'Recall Worker', description: 'Semantic search & indexing' },
  { value: 'learning', label: 'Learning Worker', description: 'Pattern transfer, meta-learning' },
  { value: 'think', label: 'Think Worker', description: 'Multi-agent committee decisions' },
];

export function WorkersTab() {
  const { workers, projects, startWorker, addToast } = useDashboard();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [formData, setFormData] = useState<WorkerStartRequest>({
    worker_type: 'analysis',
    project_id: 0,
    max_iterations: 5,
    dream_probability: 0.15,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.worker_type) {
      newErrors.worker_type = 'Worker type is required';
    }

    if (!formData.project_id || formData.project_id === 0) {
      newErrors.project_id = 'Project is required';
    }

    if (formData.max_iterations < 1 || formData.max_iterations > 100) {
      newErrors.max_iterations = 'Max iterations must be between 1 and 100';
    }

    if (formData.dream_probability < 0 || formData.dream_probability > 1) {
      newErrors.dream_probability = 'Dream probability must be between 0 and 1';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await startWorker(formData);

      addToast({
        message: `${getWorkerLabel(formData.worker_type)} started successfully!`,
        type: 'success',
      });

      // Reset form and close dialog
      setFormData({
        worker_type: 'analysis',
        project_id: 0,
        max_iterations: 5,
        dream_probability: 0.15,
      });
      setErrors({});
      setShowAdvanced(false);
      setIsFormOpen(false);
    } catch (error) {
      console.error('Error starting worker:', error);
      addToast({
        message: `Failed to start worker: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'error',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartAllWorkers = async () => {
    if (!formData.project_id || formData.project_id === 0) {
      addToast({
        message: 'Please select a project first',
        type: 'error',
      });
      return;
    }

    const confirmed = window.confirm(
      'Start all 5 workers for this project?\n\nThis will start:\n- Analysis Worker\n- Dream Worker\n- Recall Worker\n- Learning Worker\n- Think Worker'
    );

    if (!confirmed) return;

    setIsSubmitting(true);
    const workers = ['analysis', 'dream', 'recall', 'learning', 'think'] as const;
    let successCount = 0;
    let failCount = 0;

    try {
      for (const workerType of workers) {
        try {
          await startWorker({
            ...formData,
            worker_type: workerType,
          });
          successCount++;
        } catch (error) {
          console.error(`Error starting ${workerType} worker:`, error);
          failCount++;
        }
      }

      if (successCount > 0) {
        addToast({
          message: `Started ${successCount} worker(s) successfully${failCount > 0 ? `, ${failCount} failed` : ''}`,
          type: successCount === workers.length ? 'success' : 'info',
        });
      } else {
        addToast({
          message: 'Failed to start all workers',
          type: 'error',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const getWorkerLabel = (workerType: string): string => {
    const worker = WORKER_TYPES.find((w) => w.value === workerType);
    return worker ? worker.label : 'Worker';
  };

  const getProjectName = (projectId: number): string => {
    const project = projects.find((p) => p.project_id === projectId);
    if (!project) return 'Unknown';

    try {
      const url = new URL(project.repo_url);
      const parts = url.pathname.split('/').filter(Boolean);
      if (parts.length >= 2) {
        return `${parts[0]}/${parts[1].replace('.git', '')}`;
      }
    } catch {
      return project.repo_url;
    }

    return project.repo_url;
  };

  const getHealthClass = (worker: WorkerStats): string => {
    if (worker.errors > 5) return 'bg-terminal-red';
    if (worker.errors > 0) return 'bg-terminal-yellow';
    return 'bg-terminal-green';
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  };

  const dreamProbabilityPercent = Math.round(formData.dream_probability * 100);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-primary flex items-center gap-2">
          <Cpu className="h-6 w-6" />
          Worker Statistics
        </h2>
        <Button onClick={() => setIsFormOpen(true)} className="gap-2">
          <Play className="h-4 w-4" />
          Start Worker
        </Button>
      </div>

      {/* Worker Control Form Dialog */}
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="sm:max-w-[600px] bg-background-secondary border-primary/20">
          <DialogHeader>
            <DialogTitle className="text-primary flex items-center gap-2">
              <Play className="h-5 w-5" />
              Start Worker
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              Configure and start a worker for project analysis
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Worker Type */}
            <div className="space-y-2">
              <Label htmlFor="worker_type" className="text-gray-300">
                Worker Type <span className="text-terminal-red">*</span>
              </Label>
              <Select
                value={formData.worker_type}
                onValueChange={(value: string) => setFormData({ ...formData, worker_type: value as any })}
              >
                <SelectTrigger className={`terminal-border bg-background ${errors.worker_type ? 'border-terminal-red' : ''}`}>
                  <SelectValue placeholder="Select worker type..." />
                </SelectTrigger>
                <SelectContent className="bg-background-secondary border-primary/20">
                  {WORKER_TYPES.map((worker) => (
                    <SelectItem key={worker.value} value={worker.value} className="text-gray-300 focus:bg-background-tertiary focus:text-primary">
                      <div className="flex flex-col">
                        <span className="font-semibold">{worker.label}</span>
                        <span className="text-xs text-gray-500">{worker.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.worker_type && (
                <p className="text-sm text-terminal-red">{errors.worker_type}</p>
              )}
            </div>

            {/* Project */}
            <div className="space-y-2">
              <Label htmlFor="project_id" className="text-gray-300">
                Project <span className="text-terminal-red">*</span>
              </Label>
              <Select
                value={formData.project_id.toString()}
                onValueChange={(value: string) => setFormData({ ...formData, project_id: parseInt(value, 10) })}
              >
                <SelectTrigger className={`terminal-border bg-background ${errors.project_id ? 'border-terminal-red' : ''}`}>
                  <SelectValue placeholder="Select project..." />
                </SelectTrigger>
                <SelectContent className="bg-background-secondary border-primary/20">
                  {projects.map((project) => (
                    <SelectItem key={project.project_id} value={project.project_id.toString()} className="text-gray-300 focus:bg-background-tertiary focus:text-primary">
                      {getProjectName(project.project_id)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.project_id && (
                <p className="text-sm text-terminal-red">{errors.project_id}</p>
              )}
              <p className="text-sm text-gray-500">Choose the project for this worker to analyze</p>
            </div>

            {/* Advanced Options Toggle */}
            <div>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="w-full border-gray-600 text-gray-300 hover:bg-background-tertiary"
              >
                {showAdvanced ? 'Hide Advanced Options' : 'Show Advanced Options'}
              </Button>
            </div>

            {showAdvanced && (
              <>
                {/* Max Iterations */}
                <div className="space-y-2">
                  <Label htmlFor="max_iterations" className="text-gray-300">Max Iterations</Label>
                  <Input
                    id="max_iterations"
                    type="number"
                    min="1"
                    max="100"
                    value={formData.max_iterations}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
                      setFormData({ ...formData, max_iterations: parseInt(e.target.value, 10) })
                    }
                    className="terminal-border bg-background"
                  />
                  <p className="text-sm text-gray-500">Maximum number of iterations to run (1-100)</p>
                </div>

                {/* Dream Probability */}
                <div className="space-y-2">
                  <Label htmlFor="dream_probability" className="text-gray-300">
                    Dream Probability ({dreamProbabilityPercent}%)
                  </Label>
                  <input
                    id="dream_probability"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={formData.dream_probability}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => 
                      setFormData({ ...formData, dream_probability: parseFloat(e.target.value) })
                    }
                    className="w-full h-2 bg-background-tertiary rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                  <p className="text-sm text-gray-500">Probability of experimental cycles (0-100%)</p>
                </div>
              </>
            )}

            <DialogFooter className="flex flex-col gap-2 sm:flex-row">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsFormOpen(false)}
                className="border-gray-600 text-gray-300 hover:bg-background-tertiary"
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={handleStartAllWorkers}
                disabled={isSubmitting || !formData.project_id}
                className="border-primary/50 text-primary hover:bg-primary/10"
              >
                🚀 Start All Workers
              </Button>
              <Button type="submit" disabled={isSubmitting} className="bg-primary text-background hover:bg-primary/90">
                {isSubmitting ? 'Starting...' : 'Start Worker'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Worker Stats Grid */}
      {workers.length === 0 ? (
        <Card className="terminal-card p-12 text-center">
          <Activity className="h-16 w-16 mx-auto mb-4 text-gray-600" />
          <p className="text-gray-400 text-lg mb-2">No worker stats found</p>
          <p className="text-gray-500 text-sm">Start a worker to begin analysis</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {workers.map((worker: WorkerStats) => (
            <Card key={worker.worker_name} className="terminal-card p-6 hover:border-primary/50 transition-colors">
              <div className="space-y-4">
                {/* Worker Name & Health */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${getHealthClass(worker)}`} />
                    <h3 className="text-lg font-mono glow-text">{worker.worker_name}</h3>
                  </div>
                  <Cpu className="h-5 w-5 text-primary" />
                </div>

                {/* Stats Grid */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Cycles Run:</span>
                    <span className="font-mono text-terminal-blue">{worker.cycles_run}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Experiments:</span>
                    <span className="font-mono text-terminal-purple">{worker.experiments_run}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Total Time:</span>
                    <span className="font-mono text-terminal-green">{formatTime(worker.total_time)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Errors:</span>
                    <span 
                      className={`font-mono flex items-center gap-1 ${
                        worker.errors > 0 ? 'text-terminal-red' : 'text-terminal-green'
                      }`}
                    >
                      {worker.errors > 0 ? <XCircle className="h-3 w-3" /> : <CheckCircle2 className="h-3 w-3" />}
                      {worker.errors}
                    </span>
                  </div>
                </div>

                {/* Last Run */}
                {worker.last_run && (
                  <div className="text-xs text-gray-600 font-mono pt-2 border-t border-gray-800">
                    Last run: {format(new Date(worker.last_run), 'MMM d, yyyy HH:mm')}
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
