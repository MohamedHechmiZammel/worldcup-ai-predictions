interface ConfidenceMeterProps {
  confidenceLow: number;   // 0-1
  confidenceHigh: number;  // 0-1
  modelVersion?: string;   // e.g. "v1.0.0"
}

export default function ConfidenceMeter({ confidenceLow, confidenceHigh, modelVersion }: ConfidenceMeterProps) {
  const midpoint = (confidenceLow + confidenceHigh) / 2;
  const width = confidenceHigh - confidenceLow;

  const confidenceLabel = midpoint > 0.7 ? 'High' : midpoint > 0.5 ? 'Medium' : 'Low';
  const colorClass = midpoint > 0.7 ? 'text-green-400' : midpoint > 0.5 ? 'text-yellow-400' : 'text-gray-400';

  const tooltipText = modelVersion
    ? `Confidence: ${(midpoint * 100).toFixed(0)}% (±${(width / 2 * 100).toFixed(0)}%) · Predicted by model ${modelVersion}`
    : `Confidence: ${(midpoint * 100).toFixed(0)}% (±${(width / 2 * 100).toFixed(0)}%)`;

  return (
    <span
      className={`text-xs font-medium ${colorClass} cursor-help`}
      title={tooltipText}
    >
      {confidenceLabel} confidence
    </span>
  );
}
