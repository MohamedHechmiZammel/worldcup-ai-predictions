import React from 'react';

type MatchStatus = 'scheduled' | 'live' | 'halftime' | 'finished' | 'postponed' | 'cancelled';

interface LiveBadgeProps {
  status: MatchStatus;
  scheduledAt?: string; // ISO datetime string, shown for scheduled matches
}

function formatScheduledAt(iso: string): string {
  const date = new Date(iso);
  const month = date.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
  const day = date.getUTCDate();
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  return `${month} ${day} · ${hours}:${minutes} UTC`;
}

const LiveBadge: React.FC<LiveBadgeProps> = ({ status, scheduledAt }) => {
  switch (status) {
    case 'live':
      return (
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-red-400 font-bold text-xs">LIVE</span>
        </span>
      );

    case 'halftime':
      return (
        <span className="inline-flex items-center rounded-full bg-yellow-600 px-2 py-0.5 text-xs font-bold text-black">
          HT
        </span>
      );

    case 'finished':
      return (
        <span className="inline-flex items-center rounded-full bg-gray-600 px-2 py-0.5 text-xs font-bold text-gray-200">
          FT
        </span>
      );

    case 'scheduled':
      return (
        <span className="text-xs text-gray-400">
          {scheduledAt ? formatScheduledAt(scheduledAt) : '—'}
        </span>
      );

    case 'postponed':
      return (
        <span className="text-xs font-bold text-orange-400">
          POSTPONED
        </span>
      );

    case 'cancelled':
      return (
        <span className="text-xs font-bold text-red-400 line-through">
          CANCELLED
        </span>
      );

    default:
      return null;
  }
};

export default LiveBadge;
