import type { LiveMatchStateData } from '../../types';

interface LiveStatsPanelProps {
  matchState: LiveMatchStateData;
  homeTeamName: string;
  awayTeamName: string;
  isFinished?: boolean;
}

type Stats = Record<string, string | number> | null;

// ESPN scoreboard uses `shotsOnTarget`; ESPN summary uses `totalShots`
function getStat(stats: Stats, ...keys: string[]): string | number | undefined {
  if (!stats) return undefined;
  for (const key of keys) {
    if (stats[key] !== undefined) return stats[key];
  }
  return undefined;
}

function StatRow({
  label,
  home,
  away,
}: {
  label: string;
  home: string | number | undefined;
  away: string | number | undefined;
}) {
  return (
    <div className="flex items-center justify-between text-[11px] tabular-nums">
      <span className="text-slate-300 font-medium w-8 text-right">{home ?? '—'}</span>
      <span className="text-slate-500 text-[10px] uppercase tracking-widest flex-1 text-center">{label}</span>
      <span className="text-slate-300 font-medium w-8 text-left">{away ?? '—'}</span>
    </div>
  );
}

export default function LiveStatsPanel({
  matchState,
  homeTeamName,
  awayTeamName,
  isFinished = false,
}: LiveStatsPanelProps) {
  const { minute, period_description, home_stats, away_stats } = matchState;

  const homePoss = parseFloat(String(getStat(home_stats, 'possessionPct') ?? 50));
  const awayPoss = parseFloat(String(getStat(away_stats, 'possessionPct') ?? 50));

  // Label changes depending on which ESPN endpoint fed the data
  const homeShots = getStat(home_stats, 'shotsOnTarget', 'totalShots');
  const awayShots = getStat(away_stats, 'shotsOnTarget', 'totalShots');
  const shotsLabel = home_stats?.shotsOnTarget !== undefined ? 'Shots on Target' : 'Shots';

  const clockLabel = isFinished
    ? (period_description || 'Full Time')
    : minute != null && minute > 0
      ? `${minute}'${period_description ? ` · ${period_description}` : ''}`
      : period_description || 'Live';

  return (
    <div className="bg-card rounded-2xl border border-white/5 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-widest text-slate-600">
          {isFinished ? 'Match Stats' : 'Live Stats'}
        </p>
        <span className={`text-[11px] font-bold tabular-nums ${isFinished ? 'text-slate-500' : 'text-gold'}`}>
          {clockLabel}
        </span>
      </div>

      {/* Team name labels */}
      <div className="flex justify-between text-[10px] text-slate-500 uppercase tracking-widest">
        <span className="truncate max-w-[120px]">{homeTeamName}</span>
        <span className="truncate max-w-[120px] text-right">{awayTeamName}</span>
      </div>

      {/* Possession bar */}
      <div>
        <div className="flex h-2 rounded-full overflow-hidden">
          <div className="bg-blue-500 transition-all duration-700" style={{ width: `${homePoss}%` }} />
          <div className="bg-red-500 transition-all duration-700" style={{ width: `${awayPoss}%` }} />
        </div>
        <div className="flex justify-between mt-1 text-[10px] text-slate-400 tabular-nums">
          <span>{homePoss.toFixed(0)}%</span>
          <span className="text-slate-600 uppercase tracking-widest text-[9px]">Possession</span>
          <span>{awayPoss.toFixed(0)}%</span>
        </div>
      </div>

      {/* Key stats */}
      <div className="space-y-2 pt-1 border-t border-white/[0.06]">
        <StatRow label={shotsLabel} home={homeShots} away={awayShots} />
        <StatRow
          label="Corners"
          home={getStat(home_stats, 'wonCorners')}
          away={getStat(away_stats, 'wonCorners')}
        />
        <StatRow
          label="Fouls"
          home={getStat(home_stats, 'foulsCommitted')}
          away={getStat(away_stats, 'foulsCommitted')}
        />
        {/* Extra stats available from the summary endpoint (finished matches) */}
        {getStat(home_stats, 'yellowCards') !== undefined && (
          <StatRow
            label="Yellow Cards"
            home={getStat(home_stats, 'yellowCards')}
            away={getStat(away_stats, 'yellowCards')}
          />
        )}
        {getStat(home_stats, 'saves') !== undefined && (
          <StatRow
            label="Saves"
            home={getStat(home_stats, 'saves')}
            away={getStat(away_stats, 'saves')}
          />
        )}
      </div>
    </div>
  );
}
