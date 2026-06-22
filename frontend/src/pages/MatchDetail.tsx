import { useParams, Link } from 'react-router-dom';
import { useMatch, usePredictionHistory } from '../hooks/useMatch';
import { useWebSocket } from '../hooks/useWebSocket';
import { usePredictionsStore } from '../store/predictions';
import ProbabilityBar from '../components/ProbabilityBar';
import FactorsPanel from '../components/FactorsPanel';
import LiveBadge from '../components/LiveBadge';
import LiveEventLog from '../components/LiveEventLog';
import FeedStatusBanner from '../components/FeedStatusBanner';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { Factor } from '../types';

export default function MatchDetail() {
  const { id } = useParams<{ id: string }>();
  const matchId = Number(id);

  const { data: match, isLoading } = useMatch(matchId);
  const { data: history } = usePredictionHistory(matchId);
  const { connectionState } = useWebSocket(matchId);

  // Live data from Zustand store (WebSocket updates)
  const livePrediction = usePredictionsStore(s => s.predictions[matchId]);
  const liveEvents = usePredictionsStore(s => s.liveEvents[matchId] ?? []);
  const feedAvailable = usePredictionsStore(s => s.feedStatus[matchId] ?? true);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center text-gray-400">
        Loading...
      </div>
    );
  }

  if (!match) {
    return (
      <div className="min-h-screen bg-gray-900 p-8">
        <Link to="/" className="text-blue-400 hover:underline">← Dashboard</Link>
        <p className="text-red-400 mt-4">Match not found</p>
      </div>
    );
  }

  // Use live prediction if available, fall back to REST prediction
  const prediction = livePrediction ?? match.prediction;
  const factors: Factor[] = prediction?.top_factors ?? [];

  // Build probability history for sparkline chart
  const chartData = (history?.predictions ?? []).map((p, i) => ({
    name: `#${i + 1}`,
    home: Math.round(p.home_win_prob * 100),
    draw: Math.round(p.draw_prob * 100),
    away: Math.round(p.away_win_prob * 100),
  }));

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <Link to="/" className="text-blue-400 text-sm hover:underline">← All Matches</Link>
        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center gap-3">
            <LiveBadge status={match.status} scheduledAt={match.scheduled_at} />
            <span className="text-gray-400 text-sm">{match.stage}</span>
          </div>
          <span className={`text-xs px-2 py-1 rounded ${
            connectionState === 'connected' ? 'text-green-400 bg-green-900/30' :
            connectionState === 'connecting' ? 'text-yellow-400 bg-yellow-900/30' :
            'text-red-400 bg-red-900/30'
          }`}>
            {connectionState === 'connected' ? '● Live' :
             connectionState === 'connecting' ? '○ Connecting...' :
             '○ Disconnected'}
          </span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Feed status banner */}
        <FeedStatusBanner available={feedAvailable} lastUpdated={new Date()} />

        {/* Score / Teams */}
        <div className="bg-gray-800 rounded-xl p-6 text-center">
          <div className="flex items-center justify-center gap-8">
            <div className="flex-1 text-right">
              <p className="text-xl font-bold">{match.home_team?.name ?? 'Home'}</p>
              <p className="text-gray-400 text-sm">{match.home_team?.country_code}</p>
            </div>
            <div className="text-4xl font-black w-32 text-center">
              {(match.status === 'live' || match.status === 'halftime' || match.status === 'finished')
                ? `${match.home_score ?? 0} – ${match.away_score ?? 0}`
                : 'vs'
              }
            </div>
            <div className="flex-1 text-left">
              <p className="text-xl font-bold">{match.away_team?.name ?? 'Away'}</p>
              <p className="text-gray-400 text-sm">{match.away_team?.country_code}</p>
            </div>
          </div>
          {match.venue && (
            <p className="text-gray-500 text-sm mt-3">{match.venue}, {match.city}</p>
          )}
        </div>

        {/* Prediction probabilities */}
        {prediction && match.status !== 'finished' && (
          <div className="bg-gray-800 rounded-xl p-6 space-y-4">
            <h2 className="text-lg font-semibold">AI Prediction</h2>
            <ProbabilityBar
              homeWinProb={prediction.home_win_prob}
              drawProb={prediction.draw_prob}
              awayWinProb={prediction.away_win_prob}
              homeTeamName={match.home_team?.name ?? 'Home'}
              awayTeamName={match.away_team?.name ?? 'Away'}
              confidenceLow={prediction.confidence_low}
              confidenceHigh={prediction.confidence_high}
            />
            <FactorsPanel factors={factors} />
            <p className="text-xs text-gray-500">
              Expected: {prediction.expected_home_goals.toFixed(1)} – {prediction.expected_away_goals.toFixed(1)} goals
            </p>
          </div>
        )}

        {/* Probability history sparkline */}
        {chartData.length > 1 && (
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Probability Timeline</h2>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={chartData}>
                <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8 }} />
                <Legend />
                <Line type="monotone" dataKey="home" stroke="#3b82f6" strokeWidth={2} dot={false} name="Home Win %" />
                <Line type="monotone" dataKey="draw" stroke="#6b7280" strokeWidth={2} dot={false} name="Draw %" />
                <Line type="monotone" dataKey="away" stroke="#ef4444" strokeWidth={2} dot={false} name="Away Win %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Live event log */}
        {(match.status === 'live' || match.status === 'halftime' || liveEvents.length > 0) && (
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Match Events</h2>
            <LiveEventLog events={liveEvents} />
          </div>
        )}
      </main>
    </div>
  );
}
