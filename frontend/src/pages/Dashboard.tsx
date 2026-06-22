import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMatches } from '../hooks/useMatches';
import MatchCard from '../components/MatchCard';
import AccuracyPanel from '../components/AccuracyPanel';

const KNOCKOUT_STAGES = new Set(['Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Third place', 'Final']);

export default function Dashboard() {
  const { matchesByStage, isLoading, error, data } = useMatches();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const liveCount = data?.live_count ?? 0;

  const toggleStage = (stage: string) => {
    setCollapsed(prev => ({ ...prev, [stage]: !prev[stage] }));
  };

  // Group stages collapse by default; knockout stages expand
  const isCollapsed = (stage: string): boolean => {
    if (stage in collapsed) return collapsed[stage];
    return !KNOCKOUT_STAGES.has(stage);  // group stages start collapsed
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-gray-400 text-lg">Loading matches...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-red-400">Failed to load matches. Check that the backend is running.</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">⚽ World Cup 2026</h1>
            <p className="text-gray-400 text-sm">AI Prediction Dashboard</p>
          </div>
          {liveCount > 0 && (
            <span className="flex items-center gap-2 bg-red-900/50 border border-red-700 text-red-300 text-sm px-3 py-1 rounded-full">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              {liveCount} match{liveCount > 1 ? 'es' : ''} live
            </span>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Accuracy tracker */}
        <div className="mb-8">
          <AccuracyPanel />
        </div>

        {matchesByStage.size === 0 ? (
          <div className="text-center py-20 text-gray-500">
            No matches found. Run seed scripts to populate the database.
          </div>
        ) : (
          Array.from(matchesByStage.entries()).map(([stage, matches]) => {
            const open = !isCollapsed(stage);
            const hasLive = matches.some(m => m.status === 'live');
            return (
              <section key={stage} className="mb-6">
                <button
                  className="w-full flex items-center gap-3 mb-3 text-left group"
                  onClick={() => toggleStage(stage)}
                  aria-expanded={open}
                >
                  <span className="text-xs text-gray-500 transition-transform duration-200" style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                  <h2 className="text-lg font-semibold text-gray-200 group-hover:text-white transition-colors">{stage}</h2>
                  <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                    {matches.length} match{matches.length !== 1 ? 'es' : ''}
                  </span>
                  {hasLive && (
                    <span className="text-xs text-red-400 font-medium">● LIVE</span>
                  )}
                </button>
                {open && (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {matches.map(match => (
                      <MatchCard
                        key={match.id}
                        match={match}
                        onClick={() => navigate(`/match/${match.id}`)}
                      />
                    ))}
                  </div>
                )}
              </section>
            );
          })
        )}
      </main>
    </div>
  );
}
