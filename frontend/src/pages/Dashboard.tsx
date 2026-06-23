import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMatches } from '../hooks/useMatches';
import { useStandings } from '../hooks/useStandings';
import MatchCard from '../components/MatchCard';
import AccuracyPanel from '../components/AccuracyPanel';
import GroupStandings from '../components/GroupStandings';

const GROUP_LETTERS = ['A','B','C','D','E','F','G','H','I','J','K','L'];
const KNOCKOUT_STAGES = ['Round of 32','Round of 16','Quarter-finals','Semi-finals','Third place','Final'];

export default function Dashboard() {
  const { matchesByStage, isLoading, error, data } = useMatches();
  const { data: standingsData } = useStandings();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<string>('');

  const liveCount = data?.live_count ?? 0;

  // Stages present in data
  const stages = Array.from(matchesByStage.keys());
  const groupStages  = stages.filter(s => s.startsWith('Group '));
  const knockoutStagesPresent = stages.filter(s => KNOCKOUT_STAGES.includes(s));

  // Auto-select first live group, or first group available
  useEffect(() => {
    if (!activeTab && stages.length > 0) {
      const liveStage = stages.find(s =>
        (matchesByStage.get(s) ?? []).some(m => m.status === 'live')
      );
      setActiveTab(liveStage ?? stages[0]);
    }
  }, [stages.join(',')]);

  const activeMatches = matchesByStage.get(activeTab) ?? [];
  const activeLetter = activeTab.replace('Group ', '');

  if (isLoading) {
    return (
      <div className="min-h-screen bg-pitch flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="font-display text-5xl font-bold text-gold animate-pulse">WC26</div>
          <p className="text-slate-500 text-sm tracking-widest uppercase">Loading matches…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-pitch flex items-center justify-center p-8">
        <p className="text-red-400">Failed to load matches. Check that the backend is running.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-pitch text-slate-100">
      {/* ── Header ── */}
      <header className="sticky top-0 z-20 bg-pitch/95 backdrop-blur border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          {/* Title row */}
          <div className="flex items-center justify-between py-3">
            <div className="flex items-baseline gap-3">
              <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-wide text-white">
                FIFA WORLD CUP 2026™
              </h1>
              <span className="hidden sm:inline text-[11px] uppercase tracking-widest text-slate-500 font-medium">
                AI Predictions
              </span>
            </div>
            {liveCount > 0 ? (
              <span className="flex items-center gap-2 bg-green-500/10 border border-green-500/30 text-green-400 text-xs font-semibold px-3 py-1.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                {liveCount} LIVE
              </span>
            ) : (
              <AccuracyPanel compact />
            )}
          </div>

          {/* ── Group / Stage tabs ── */}
          {stages.length > 0 && (
            <div className="flex items-center gap-1 overflow-x-auto scrollbar-none pb-2 -mx-1 px-1">
              {/* Group tabs */}
              {groupStages.length > 0 && (
                <>
                  <span className="text-[10px] uppercase tracking-widest text-slate-600 font-medium mr-1 flex-shrink-0">
                    Group
                  </span>
                  {GROUP_LETTERS.filter(l => groupStages.includes(`Group ${l}`)).map(letter => {
                    const stage = `Group ${letter}`;
                    const isActive = activeTab === stage;
                    const hasLive = (matchesByStage.get(stage) ?? []).some(m => m.status === 'live');
                    return (
                      <button
                        key={stage}
                        onClick={() => setActiveTab(stage)}
                        className={`relative flex-shrink-0 w-9 h-9 rounded-lg font-display text-base font-bold transition-all duration-150
                          ${isActive
                            ? 'bg-gold text-pitch shadow-lg shadow-gold/20'
                            : 'text-slate-400 hover:text-white hover:bg-white/5'
                          }`}
                      >
                        {letter}
                        {hasLive && (
                          <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-green-500 rounded-full" />
                        )}
                      </button>
                    );
                  })}
                </>
              )}

              {/* Separator */}
              {knockoutStagesPresent.length > 0 && (
                <span className="w-px h-5 bg-white/10 mx-2 flex-shrink-0" />
              )}

              {/* Knockout stage tabs */}
              {knockoutStagesPresent.map(stage => {
                const isActive = activeTab === stage;
                const short: Record<string,string> = {
                  'Round of 32': 'R32', 'Round of 16': 'R16',
                  'Quarter-finals': 'QF', 'Semi-finals': 'SF',
                  'Third place': '3rd', 'Final': 'F',
                };
                return (
                  <button
                    key={stage}
                    onClick={() => setActiveTab(stage)}
                    className={`flex-shrink-0 px-3 h-9 rounded-lg font-display text-sm font-bold transition-all duration-150
                      ${isActive
                        ? 'bg-gold text-pitch shadow-lg shadow-gold/20'
                        : 'text-slate-400 hover:text-white hover:bg-white/5'
                      }`}
                  >
                    {short[stage] ?? stage}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </header>

      {/* ── Main content ── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Accuracy strip (shown below header on small screens) */}
        {liveCount > 0 && (
          <div className="mb-4">
            <AccuracyPanel compact />
          </div>
        )}

        {matchesByStage.size === 0 ? (
          <div className="text-center py-24 space-y-2">
            <p className="font-display text-4xl font-bold text-slate-700">NO MATCHES YET</p>
            <p className="text-slate-600 text-sm">Run the seed scripts to populate the database.</p>
          </div>
        ) : (
          activeTab && (
            <div className="animate-fade-in">
              {/* Stage heading */}
              <div className="flex items-baseline gap-3 mb-5">
                <h2 className="font-display text-3xl font-black tracking-wide text-white">
                  {activeTab.startsWith('Group ')
                    ? <>GROUP <span className="text-gold">{activeLetter}</span></>
                    : activeTab.toUpperCase()
                  }
                </h2>
                <span className="text-slate-600 text-sm">
                  {activeMatches.length} match{activeMatches.length !== 1 ? 'es' : ''}
                </span>
              </div>

              {/* Match grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {activeMatches.map(match => (
                  <MatchCard
                    key={match.id}
                    match={match}
                    onClick={() => navigate(`/match/${match.id}`)}
                  />
                ))}
              </div>

              {/* Group standings — only for group stage tabs */}
              {activeTab.startsWith('Group ') && (
                <div className="mt-6">
                  <GroupStandings
                    matches={activeMatches}
                    groupLetter={activeLetter}
                    liveStandings={standingsData?.groups?.[activeLetter]}
                  />
                </div>
              )}
            </div>
          )
        )}
      </main>
    </div>
  );
}
