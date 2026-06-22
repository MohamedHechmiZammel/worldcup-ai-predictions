interface AIResultBadgeProps {
  wasCorrect: boolean;
  predictedOutcome: string;
  actualOutcome: string;
}

const OUTCOME_LABELS: Record<string, string> = {
  home_win: 'Home Win',
  draw: 'Draw',
  away_win: 'Away Win',
};

export default function AIResultBadge({ wasCorrect, predictedOutcome, actualOutcome }: AIResultBadgeProps) {
  const label = wasCorrect ? '✓ AI predicted correctly' : '✗ AI missed this one';
  const colorClass = wasCorrect
    ? 'text-green-400 bg-green-900/30 border-green-800'
    : 'text-red-400 bg-red-900/30 border-red-800';

  const tooltip = wasCorrect
    ? `Predicted: ${OUTCOME_LABELS[predictedOutcome] ?? predictedOutcome}`
    : `Predicted: ${OUTCOME_LABELS[predictedOutcome] ?? predictedOutcome} · Actual: ${OUTCOME_LABELS[actualOutcome] ?? actualOutcome}`;

  return (
    <div
      className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded border ${colorClass} cursor-help`}
      title={tooltip}
    >
      <span>{label}</span>
    </div>
  );
}
