import React from "react";

interface Factor {
  feature: string;
  impact_pct: number;
  label: string;
}

interface FactorsPanelProps {
  factors: Factor[];
  title?: string;
}

const RANK_COLORS: Record<number, { badge: string; bar: string }> = {
  0: { badge: "bg-green-500 text-white", bar: "bg-green-500" },
  1: { badge: "bg-amber-500 text-white", bar: "bg-amber-500" },
  2: { badge: "bg-orange-500 text-white", bar: "bg-orange-500" },
};

const FactorsPanel: React.FC<FactorsPanelProps> = ({
  factors,
  title = "Why this prediction?",
}) => {
  const displayedFactors = factors.slice(0, 3);
  const hasLimitedData = factors.length > 0 && factors.length < 3;

  return (
    <div className="rounded-lg bg-gray-900 p-4 space-y-3">
      {/* Title */}
      <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
        {title}
      </p>

      {displayedFactors.length === 0 ? (
        <p className="text-sm italic text-gray-500">
          Prediction factors will appear once the match is analyzed
        </p>
      ) : (
        <ul className="space-y-3">
          {displayedFactors.map((factor, idx) => {
            const colors = RANK_COLORS[idx] ?? RANK_COLORS[2];
            return (
              <li key={factor.feature} className="space-y-1">
                <div className="flex items-center gap-3">
                  {/* Impact badge */}
                  <span
                    className={`inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-bold tabular-nums ${colors.badge}`}
                    aria-label={`Impact: ${factor.impact_pct}%`}
                  >
                    {factor.impact_pct}%
                  </span>

                  {/* Label */}
                  <span className="flex-1 text-sm text-gray-100">
                    {factor.label}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="h-1 w-full rounded-full bg-gray-700">
                  <div
                    className={`h-1 rounded-full transition-all duration-500 ${colors.bar}`}
                    style={{ width: `${Math.min(factor.impact_pct, 100)}%` }}
                    role="progressbar"
                    aria-valuenow={factor.impact_pct}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
              </li>
            );
          })}

          {/* Limited data badge */}
          {hasLimitedData && (
            <li>
              <span className="inline-flex items-center rounded-full border border-gray-600 px-2.5 py-0.5 text-xs text-gray-400">
                Limited data
              </span>
            </li>
          )}
        </ul>
      )}
    </div>
  );
};

export default FactorsPanel;
