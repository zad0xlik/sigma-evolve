import { useDashboardStore } from '@/stores/dashboardStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';

export function PatternsTab() {
  const patterns = useDashboardStore((state) => state.patterns);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    try {
      return format(new Date(dateString), 'MMM d, yyyy h:mm a');
    } catch {
      return dateString;
    }
  };

  const formatConfidence = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-primary glow-text">🧬 Learned Patterns</h2>
        <div className="text-sm text-gray-400">
          {patterns.length} {patterns.length === 1 ? 'pattern' : 'patterns'}
        </div>
      </div>

      {patterns.length === 0 ? (
        <Card className="terminal-card">
          <CardContent className="pt-6">
            <p className="text-center text-gray-400 py-8">No patterns found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {patterns.map((pattern) => (
            <Card key={pattern.pattern_id} className="terminal-card">
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <CardTitle className="text-lg text-gray-100">
                    {pattern.pattern_name}
                  </CardTitle>
                  <Badge className="bg-primary/20 text-primary border-primary">
                    {pattern.pattern_type}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {pattern.description && (
                  <p className="text-gray-400 text-sm">{pattern.description}</p>
                )}

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400 font-semibold">Language:</span>{' '}
                    <span className="text-gray-200">{pattern.language}</span>
                  </div>

                  {pattern.framework && (
                    <div>
                      <span className="text-gray-400 font-semibold">Framework:</span>{' '}
                      <span className="text-gray-200">{pattern.framework}</span>
                    </div>
                  )}

                  {pattern.domain && (
                    <div>
                      <span className="text-gray-400 font-semibold">Domain:</span>{' '}
                      <span className="text-gray-200">{pattern.domain}</span>
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400 font-semibold">Confidence:</span>
                    <span className="text-primary">{formatConfidence(pattern.confidence)}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div 
                      className="bg-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${pattern.confidence * 100}%` }}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-6 text-sm">
                  <div>
                    <span className="text-gray-400 font-semibold">Success:</span>{' '}
                    <span className="text-green-400">{pattern.success_count}</span>
                  </div>
                  <div>
                    <span className="text-gray-400 font-semibold">Failures:</span>{' '}
                    <span className="text-red-400">{pattern.failure_count}</span>
                  </div>
                  <div>
                    <span className="text-gray-400 font-semibold">Success Rate:</span>{' '}
                    <span className="text-gray-200">
                      {pattern.success_count + pattern.failure_count > 0
                        ? `${((pattern.success_count / (pattern.success_count + pattern.failure_count)) * 100).toFixed(1)}%`
                        : 'N/A'}
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-gray-700">
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Created: {formatDate(pattern.created_at)}</span>
                    {pattern.last_used && (
                      <span>Last used: {formatDate(pattern.last_used)}</span>
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
