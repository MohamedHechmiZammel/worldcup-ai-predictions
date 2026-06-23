import { useState } from 'react';
import type { Match, Team, TeamStanding, LiveStandingEntry } from '../../types';
import { getFlag } from '../../utils/flags';

interface GroupStandingsProps {
  matches: Match[];
  groupLetter?: string;
  liveStandings?: LiveStandingEntry[]; // from ESPN API (real data)
}

// ── Client-side fallback calculations ────────────────────────────────────────

function initStanding(team: Team): TeamStanding {
  return { team, played: 0, won: 0, drawn: 0, lost: 0, goalsFor: 0, goalsAgainst: 0, goalDiff: 0, points: 0 };
}

function sortStandings(standings: TeamStanding[]): TeamStanding[] {
  return standings.sort((a, b) =>
    b.points - a.points ||
    b.goalDiff - a.goalDiff ||
    b.goalsFor - a.goalsFor
  );
}

function computeProjectedStandings(matches: Match[], liveBase?: LiveStandingEntry[]): TeamStanding[] {
  const map = new Map<string, TeamStanding>();

  // Seed map from live standings (real results so far)
  if (liveBase) {
    for (const m of matches) {
      if (!m.home_team || !m.away_team) continue;
      if (!map.has(m.home_team.country_code)) {
        const live = liveBase.find(e => e.team_abbr === m.home_team!.country_code);
        if (live) {
          map.set(m.home_team.country_code, {
            team: m.home_team,
            played: live.played,
            won: live.won,
            drawn: live.drawn,
            lost: live.lost,
            goalsFor: live.goals_for,
            goalsAgainst: live.goals_against,
            goalDiff: live.goal_diff,
            points: live.points,
          });
        } else {
          map.set(m.home_team.country_code, initStanding(m.home_team));
        }
      }
      if (!map.has(m.away_team.country_code)) {
        const live = liveBase.find(e => e.team_abbr === m.away_team!.country_code);
        if (live) {
          map.set(m.away_team.country_code, {
            team: m.away_team,
            played: live.played,
            won: live.won,
            drawn: live.drawn,
            lost: live.lost,
            goalsFor: live.goals_for,
            goalsAgainst: live.goals_against,
            goalDiff: live.goal_diff,
            points: live.points,
          });
        } else {
          map.set(m.away_team.country_code, initStanding(m.away_team));
        }
      }
    }
  } else {
    // No live data — seed from finished matches
    for (const m of matches) {
      if (!m.home_team || !m.away_team) continue;
      if (!map.has(m.home_team.country_code)) map.set(m.home_team.country_code, initStanding(m.home_team));
      if (!map.has(m.away_team.country_code)) map.set(m.away_team.country_code, initStanding(m.away_team));
      if (m.status === 'finished') {
        const hs = m.home_score ?? 0;
        const as = m.away_score ?? 0;
        const home = map.get(m.home_team.country_code)!;
        const away = map.get(m.away_team.country_code)!;
        home.played++; away.played++;
        home.goalsFor += hs; home.goalsAgainst += as;
        away.goalsFor += as; away.goalsAgainst += hs;
        if (hs > as) { home.won++; home.points += 3; away.lost++; }
        else if (hs < as) { away.won++; away.points += 3; home.lost++; }
        else { home.drawn++; home.points++; away.drawn++; away.points++; }
      }
    }
  }

  // Add AI expected points for remaining scheduled matches
  for (const m of matches) {
    if (m.status !== 'scheduled' || !m.prediction || !m.home_team || !m.away_team) continue;
    const p = m.prediction;
    const home = map.get(m.home_team.country_code);
    const away = map.get(m.away_team.country_code);
    if (!home || !away) continue;
    home.projected = true; away.projected = true;
    home.points += 3 * p.home_win_prob + p.draw_prob;
    away.points += 3 * p.away_win_prob + p.draw_prob;
    home.goalsFor += p.expected_home_goals;
    home.goalsAgainst += p.expected_away_goals;
    away.goalsFor += p.expected_away_goals;
    away.goalsAgainst += p.expected_home_goals;
  }

  return sortStandings(
    Array.from(map.values()).map(s => ({
      ...s,
      goalDiff: s.goalsFor - s.goalsAgainst,
      goalsFor: Math.round(s.goalsFor * 10) / 10,
      goalsAgainst: Math.round(s.goalsAgainst * 10) / 10,
      points: Math.round(s.points * 10) / 10,
    }))
  );
}

// ── Row helper ────────────────────────────────────────────────────────────────

type Row = {
  abbr: string;
  name: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gd: number | string;
  pts: number | string;
  projected: boolean;
};

export default function GroupStandings({ matches, liveStandings }: GroupStandingsProps) {
  const [view, setView] = useState<'current' | 'projected'>('current');

  const hasRemaining = matches.some(m => m.status === 'scheduled' && m.prediction);

  // ── Current: live ESPN data (preferred) or computed from match scores ──
  const currentRows: Row[] = (liveStandings ?? []).map(e => ({
    abbr: e.team_abbr,
    name: e.team_name,
    played: e.played,
    won: e.won,
    drawn: e.drawn,
    lost: e.lost,
    gd: e.goal_diff,
    pts: e.points,
    projected: false,
  }));

  // ── Projected: current standings + AI expected points for remaining ──
  const projectedBase = computeProjectedStandings(matches, liveStandings);
  const projectedRows: Row[] = projectedBase.map(s => ({
    abbr: s.team.country_code,
    name: s.team.name,
    played: s.played,
    won: s.won,
    drawn: s.drawn,
    lost: s.lost,
    gd: typeof s.goalDiff === 'number' ? s.goalDiff : s.goalDiff,
    pts: s.points,
    projected: !!s.projected,
  }));

  const rows = view === 'current' ? currentRows : projectedRows;
  const hasCurrentData = currentRows.length > 0;

  if (rows.length === 0) return null;

  return (
    <div className="bg-card rounded-2xl border border-white/5 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <p className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">Standings</p>
          {hasCurrentData && (
            <span className="text-[9px] text-green-400/70 uppercase tracking-widest">● Live</span>
          )}
        </div>
        {hasRemaining && (
          <div className="flex rounded-lg overflow-hidden border border-white/10 text-[10px] font-bold uppercase tracking-wider">
            <button
              onClick={() => setView('current')}
              className={`px-3 py-1 transition-colors ${view === 'current' ? 'bg-gold text-pitch' : 'text-slate-500 hover:text-slate-300'}`}
            >
              Current
            </button>
            <button
              onClick={() => setView('projected')}
              className={`px-3 py-1 transition-colors ${view === 'projected' ? 'bg-gold text-pitch' : 'text-slate-500 hover:text-slate-300'}`}
            >
              AI Projected
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-slate-600 text-[10px] uppercase tracking-wider border-b border-white/[0.04]">
              <th className="text-left px-4 py-2 w-6">#</th>
              <th className="text-left px-2 py-2">Team</th>
              <th className="text-center px-2 py-2 w-8">P</th>
              <th className="text-center px-2 py-2 w-8">W</th>
              <th className="text-center px-2 py-2 w-8">D</th>
              <th className="text-center px-2 py-2 w-8">L</th>
              <th className="text-center px-2 py-2 w-10">GD</th>
              <th className="text-center px-4 py-2 w-12 text-slate-400 font-bold">Pts</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const advance = i < 2;
              const gdNum = typeof r.gd === 'string' ? parseInt(r.gd.replace('+', '')) : r.gd;
              const isProjectedRow = view === 'projected' && r.projected;
              const ptsDisplay = typeof r.pts === 'number'
                ? (isProjectedRow ? r.pts.toFixed(1) : r.pts.toString())
                : r.pts;
              const gdDisplay = typeof gdNum === 'number'
                ? (gdNum > 0 ? `+${gdNum}` : gdNum.toString())
                : r.gd;

              return (
                <tr
                  key={r.abbr}
                  className={`border-b border-white/[0.03] ${advance ? 'hover:bg-green-500/5' : 'hover:bg-white/[0.02]'}`}
                >
                  <td className="px-4 py-2.5">
                    <span className={`font-bold tabular-nums ${
                      i === 0 ? 'text-green-400' : i === 1 ? 'text-green-400' :
                      i === 2 ? 'text-slate-400' : 'text-slate-600'
                    }`}>{i + 1}</span>
                  </td>
                  <td className="px-2 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="text-base leading-none select-none">{getFlag(r.abbr)}</span>
                      <span className={`font-medium truncate max-w-[120px] ${advance ? 'text-white' : 'text-slate-400'}`}>
                        {r.name}
                      </span>
                      {isProjectedRow && (
                        <span className="text-[9px] text-gold/50 uppercase tracking-widest flex-shrink-0">proj</span>
                      )}
                    </div>
                  </td>
                  <td className="text-center px-2 py-2.5 text-slate-500 tabular-nums">{r.played}</td>
                  <td className="text-center px-2 py-2.5 text-slate-400 tabular-nums">{r.won}</td>
                  <td className="text-center px-2 py-2.5 text-slate-400 tabular-nums">{r.drawn}</td>
                  <td className="text-center px-2 py-2.5 text-slate-400 tabular-nums">{r.lost}</td>
                  <td className={`text-center px-2 py-2.5 tabular-nums ${
                    typeof gdNum === 'number' && gdNum > 0 ? 'text-green-400' :
                    typeof gdNum === 'number' && gdNum < 0 ? 'text-red-400' : 'text-slate-500'
                  }`}>
                    {gdDisplay}
                  </td>
                  <td className="text-center px-4 py-2.5">
                    <span className={`font-display font-black text-base tabular-nums ${advance ? 'text-white' : 'text-slate-500'}`}>
                      {ptsDisplay}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 flex items-center gap-4 border-t border-white/[0.04]">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-green-500/40" />
          <span className="text-[10px] text-slate-600">Qualifies (top 2)</span>
        </div>
        {view === 'projected' && (
          <span className="text-[10px] text-slate-600 ml-auto">
            Projected = actual + AI expected pts
          </span>
        )}
      </div>
    </div>
  );
}
