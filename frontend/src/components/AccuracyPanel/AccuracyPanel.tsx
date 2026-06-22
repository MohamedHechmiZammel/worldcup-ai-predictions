import { useQuery } from '@tanstack/react-query';
import { api } from '../../services/api';

export default function AccuracyPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ['accuracy'],
    queryFn: api.getAccuracy,
    refetchInterval: 60_000,  // refresh every minute
    staleTime: 30_000,
  });

  if (isLoading || !data) return null;
  if (data.total_predictions === 0) return null;

  const stages = Object.entries(data.by_stage).sort(([, a], [, b]) => b - a);

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
      <h2 className="text-lg font-semibold mb-4">AI Prediction Accuracy</h2>

      {/* Overall accuracy */}
      <div className="flex items-center gap-4 mb-4">
        <div className="text-4xl font-black text-blue-400">
          {data.accuracy_pct.toFixed(1)}%
        </div>
        <div className="text-gray-400 text-sm">
          <p>{data.correct_predictions} correct</p>
          <p>of {data.total_predictions} predictions</p>
        </div>
      </div>

      {/* By stage */}
      {stages.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 uppercase tracking-wide">By Stage</p>
          {stages.map(([stage, pct]) => (
            <div key={stage} className="flex items-center gap-3">
              <span className="text-xs text-gray-400 w-28 truncate">{stage}</span>
              <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                <div
                  className="bg-blue-500 h-1.5 rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(100, pct)}%` }}
                />
              </div>
              <span className="text-xs text-gray-300 w-10 text-right">{pct.toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
