import React from "react";

interface Factor {
  feature: string;
  impact_pct: number;
  label: string;
}

interface FactorsPanelProps {
  factors: Factor[];
}

const ACCENT = ['text-blue-400', 'text-gold', 'text-slate-300'] as const;

const FactorsPanel: React.FC<FactorsPanelProps> = ({ factors }) => {
  const items = factors.slice(0, 3);
  if (items.length === 0) return null;

  return (
    <div className="space-y-2.5">
      <p className="text-[10px] uppercase tracking-widest text-slate-600">Why this prediction?</p>
      <ul className="space-y-2">
        {items.map((f, i) => (
          <li key={f.feature} className="flex items-start gap-2.5">
            <span className={`font-display font-black text-lg leading-tight tabular-nums w-8 flex-shrink-0 ${ACCENT[i]}`}>
              {Math.round(f.impact_pct)}%
            </span>
            <div className="flex-1 min-w-0 space-y-0.5">
              <p className="text-xs text-slate-300 leading-snug">{f.label}</p>
              <div className="h-px bg-slate-800 overflow-hidden rounded-full">
                <div
                  className="h-px bg-slate-600 transition-all duration-500"
                  style={{ width: `${Math.min(f.impact_pct, 100)}%` }}
                />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FactorsPanel;
