import { useState } from 'react';
import type { Match, Team, TeamStanding } from '../../types';
import { getFlag } from '../../utils/flags';

interface GroupStandingsProps {
  matches: Match[];
}

function initStanding(team: Team): TeamStanding {
  return { team, played: 0, won: 0, drawn: 0, lost: 0, goalsFor: 0, goalsAgainst: 0, goalDiff: 0, points: 0 };
}

function computeCurrentStandings(matches: Match[]): TeamStanding[] {
  const map = new Map<number, TeamStanding>();

  for (const m of matches) {
    if (m.status !== 'finished') continue;
    const hs = m.home_score ?? 0;
    const as = m.away_score ?? 0;
    if (!m.home_team || !m.away_team) continue;

    if (!map.has(m.home_team_id)) map.set(m.home_team_id, initStanding(m.home_team));
    if (!map.has(m.away_team_id)) map.set(m.away_team_id, initStanding(m.away_team));

    const home = map.get(m.home_team_id)!;
    const away = map.get(m.away_team_id)!;

    home.played++; away.played++;
    home.goalsFor += hs; home.goalsAgainst += as;
    away.goalsFor += as; away.goalsAgainst += hs;

    if (hs > as) { home.won++; home.points += 3; away.lost++; }
    else if (hs < as) { away.won++; away.points += 3; home.lost++; }
    else { home.drawn++; home.points++; away.drawn++; away.points++; }

    home.goalDiff = home.goalsFor - home.goalsAgainst;
    away.goalDiff = away.goalsFor - away.goalsAgainst;
  }

  // Ensure all teams in the group appear even with 0 games
  for (const m of matches) {
    if (m.home_team && !map.has(m.home_team_id)) map.set(m.home_team_id, initStanding(m.home_team));
    if (m.away_team && !map.has(m.away_team_id)) map.set(m.away_team_id, initStanding(m.away_team));
  }

  return sortStandings(Array.from(map.values()));
}

function computeProjectedStandings(matches: Match[]): TeamStanding[] {
  // Start from current real standings
  const map = new Map<number, TeamStanding>();

  for (const m of matches) {
    if (!m.home_team || !m.away_team) continue;
    if (!map.has(m.home_team_id)) map.set(m.home_team_id, initStanding(m.home_team));
    if (!map.has(m.away_team_id)) map.set(m.away_team_id, initStanding(m.away_team));

    if (m.status === 'finished') {
      const hs = m.home_score ?? 0;
      const as = m.away_score ?? 0;
      const home = map.get(m.home_team_id)!;
      const away = map.get(m.away_team_id)!;

      home.played++; away.played++;
      home.goalsFor += hs; home.goalsAgainst += as;
      away.goalsFor += as; away.goalsAgainst += hs;

      if (hs > as) { home.won++; home.points += 3; away.lost++; }
      else if (hs < as) { away.won++; away.points += 3; home.lost++; }
      else { home.drawn++; home.points++; away.drawn++; away.points++; }
    } else if (m.prediction) {
      // Add expected points from AI prediction
      const p = m.prediction;
      const home = map.get(m.home_team_id)!;
      const away = map.get(m.away_team_id)!;

      home.projected = true; away.projected = true;
      home.points += 3 * p.home_win_prob + p.draw_prob;
      away.points += 3 * p.away_win_prob + p.draw_prob;

      // Projected goals from expected goals
      home.goalsFor += p.expected_home_goals;
      home.goalsAgainst += p.expected_away_goals;
      away.goalsFor += p.expected_away_goals;
      away.goalsAgainst += p.expected_home_goals;
    }
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

function sortStandings(standings: TeamStanding[]): TeamStanding[] {
  return standings.sort((a, b) =>
    b.points - a.points ||
    b.goalDiff - a.goalDiff ||
    b.goalsFor - a.goalsFor
  );
}

const POS_COLORS = ['text-green-400', 'text-green-400', 'text-slate-400', 'text-slate-600'];

export default function GroupStandings({ matches }: GroupStandingsProps) {
  const [view, setView] = useState<'current' | 'projected'>('current');

  const currentStandings = computeCurrentStandings(matches);
  const projectedStandings = computeProjectedStandings(matches);

  const standings = view === 'current' ? currentStandings : projectedStandings;
  const hasFinished = matches.some(m => m.status === 'finished');
  const hasRemaining = matches.some(m => m.status === 'scheduled' && m.prediction);

  if (standings.length === 0) return null;

  return (
    <div className="bg-card rounded-2xl border border-white/5 overflow-hidden">
      {/* Header with toggle */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <p className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">Group Standings</p>
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
              <th className="text-center px-4 py-2 w-10 font-bold text-slate-400">Pts</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((s, i) => {
              const advance = i < 2; // top 2 qualify
              return (
                <tr
                  key={s.team.id}
                  className={`border-b border-white/[0.03] transition-colors ${advance ? 'hover:bg-green-500/5' : 'hover:bg-white/[0.02]'}`}
                >
                  <td className="px-4 py-2.5">
                    <span className={`font-bold tabular-nums ${POS_COLORS[i] ?? 'text-slate-600'}`}>{i + 1}</span>
                  </td>
                  <td className="px-2 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="text-base leading-none select-none">{getFlag(s.team.country_code)}</span>
                      <span className={`font-medium truncate max-w-[110px] ${advance ? 'text-white' : 'text-slate-400'}`}>
                        {s.team.name}
                      </span>
                      {view === 'projected' && s.projected && (
                        <span className="text-[9px] text-gold/60 uppercase tracking-widest flex-shrink-0">proj</span>
                      )}
                    </div>
                  </td>
                  <td className="text-center px-2 py-2.5 text-slate-500 tabular-nums">{s.played}</td>
                  <td className="text-center px-2 py-2.5 text-slate-400 tabular-nums">{s.won}</td>
                  <td className="text-center px-2 py-2.5 text-slate-400 tabular-nums">{s.drawn}</td>
                  <td className="text-center px-2 py-2.5 text-slate-400 tabular-nums">{s.lost}</td>
                  <td className={`text-center px-2 py-2.5 tabular-nums ${s.goalDiff > 0 ? 'text-green-400' : s.goalDiff < 0 ? 'text-red-400' : 'text-slate-500'}`}>
                    {s.goalDiff > 0 ? '+' : ''}{typeof s.goalDiff === 'number' ? s.goalDiff.toFixed(view === 'projected' && s.projected ? 1 : 0) : s.goalDiff}
                  </td>
                  <td className="text-center px-4 py-2.5">
                    <span className={`font-display font-black text-base tabular-nums ${advance ? 'text-white' : 'text-slate-500'}`}>
                      {typeof s.points === 'number' ? (view === 'projected' && s.projected ? s.points.toFixed(1) : s.points.toFixed(0)) : s.points}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="px-4 py-2 flex items-center gap-4 border-t border-white/[0.04]">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-green-500/40" />
          <span className="text-[10px] text-slate-600">Qualifies</span>
        </div>
        {view === 'projected' && (
          <span className="text-[10px] text-slate-600 ml-auto">
            Points = actual + AI expected pts for remaining
          </span>
        )}
        {!hasFinished && view === 'current' && (
          <span className="text-[10px] text-slate-600">No matches played yet</span>
        )}
      </div>
    </div>
  );
}
