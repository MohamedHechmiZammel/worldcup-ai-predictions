import { useQuery } from '@tanstack/react-query';
import { api } from '../../services/api';

interface AccuracyPanelProps {
  compact?: boolean;
}

export default function AccuracyPanel({ compact = false }: AccuracyPanelProps) {
  const { data } = useQuery({
    queryKey: ['accuracy'],
    queryFn: api.getAccuracy,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  if (!data || data.total_predictions === 0) return null;

  const pct = data.accuracy_pct.toFixed(1);

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span className="font-display text-base font-bold text-gold">{pct}%</span>
        <span>model accuracy</span>
        <span className="text-slate-700">({data.correct_predictions}/{data.total_predictions})</span>
      </div>
    );
  }

  const stages = Object.entries(data.by_stage).sort(([, a], [, b]) => b - a);

  return (
    <div className="bg-card rounded-xl border border-white/5 p-5">
      <p className="text-[11px] uppercase tracking-widest text-slate-500 mb-3">AI Prediction Accuracy</p>

      <div className="flex items-baseline gap-3 mb-4">
        <span className="font-display text-5xl font-black text-gold">{pct}%</span>
        <div className="text-slate-500 text-xs leading-relaxed">
          <p className="text-slate-300 font-medium">{data.correct_predictions} correct</p>
          <p>of {data.total_predictions} completed</p>
        </div>
      </div>

      {stages.length > 0 && (
        <div className="space-y-2">
          {stages.map(([stage, p]) => (
            <div key={stage} className="flex items-center gap-3">
              <span className="text-[11px] text-slate-500 w-24 truncate">{stage}</span>
              <div className="flex-1 bg-slate-800 rounded-full h-1">
                <div
                  className="bg-gold h-1 rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(100, p)}%` }}
                />
              </div>
              <span className="text-[11px] text-slate-400 w-9 text-right tabular-nums">{p.toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
