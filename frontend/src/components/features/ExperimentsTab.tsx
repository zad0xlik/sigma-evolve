import { useDashboardStore } from '@/stores/dashboardStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Experiment } from '@/types';
import { format } from 'date-fns';

export function ExperimentsTab() {
  const experiments = useDashboardStore((state) => state.experiments);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    try {
      return format(new Date(dateString), 'MMM d, yyyy h:mm a');
    } catch {
      return dateString;
    }
  };

  const formatConfidence = (value: number | null) => {
    if (value === null) return 'N/A';
    return `${(value * 100).toFixed(1)}%`;
  };

  const getExperimentClass = (exp: Experiment) => {
    if (exp.promoted_to_production) return 'border-green-500';
    if (exp.success === true) return 'border-blue-500';
    if (exp.success === false) return 'border-red-500';
    return 'border-gray-700';
  };

  const getSuccessIndicator = (exp: Experiment) => {
    if (exp.promoted_to_production) return '🏆 Promoted';
    if (exp.success === true) return '✓ Success';
    if (exp.success === false) return '✗ Failed';
    return '⏳ Running';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-primary glow-text">🧪 Experimental Approaches</h2>
        <div className="text-sm text-gray-400">
          {experiments.length} {experiments.length === 1 ? 'experiment' : 'experiments'}
        </div>
      </div>

      {experiments.length === 0 ? (
        <Card className="terminal-card">
          <CardContent className="pt-6">
            <p className="text-center text-gray-400 py-8">No experiments found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {experiments.map((exp) => (
            <Card key={exp.experiment_id} className={`terminal-card border-l-4 ${getExperimentClass(exp)}`}>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <CardTitle className="text-lg text-gray-100">
                    {exp.experiment_name}
                  </CardTitle>
                  {exp.promoted_to_production && (
                    <Badge className="bg-green-500/20 text-green-400 border-green-500">
                      🏆 PROMOTED
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400 font-semibold min-w-[100px]">Worker:</span>
                    <span className="text-gray-200">{exp.worker_name}</span>
                  </div>

                  {exp.hypothesis && (
                    <div className="flex items-start gap-2">
                      <span className="text-gray-400 font-semibold min-w-[100px]">Hypothesis:</span>
                      <span className="text-gray-200 flex-1">{exp.hypothesis}</span>
                    </div>
                  )}

                  {exp.approach && (
                    <div className="flex items-start gap-2">
                      <span className="text-gray-400 font-semibold min-w-[100px]">Approach:</span>
                      <span className="text-gray-200 flex-1">{exp.approach}</span>
                    </div>
                  )}

                  {exp.improvement !== null && (
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400 font-semibold min-w-[100px]">Improvement:</span>
                      <span className={`font-semibold ${
                        exp.improvement > 0 ? 'text-green-400' : 
                        exp.improvement < 0 ? 'text-red-400' : 
                        'text-gray-400'
                      }`}>
                        {formatConfidence(exp.improvement)}
                      </span>
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    <span className="text-gray-400 font-semibold min-w-[100px]">Status:</span>
                    <span className="text-gray-200">{getSuccessIndicator(exp)}</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-gray-700">
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Created: {formatDate(exp.created_at)}</span>
                    {exp.completed_at && (
                      <span>Completed: {formatDate(exp.completed_at)}</span>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
