import React from 'react';

type MatchStatus = 'scheduled' | 'live' | 'halftime' | 'finished' | 'postponed' | 'cancelled';

interface LiveBadgeProps {
  status: MatchStatus;
  scheduledAt?: string;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const month = d.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' }).toUpperCase();
  const day = d.getUTCDate();
  const hh = String(d.getUTCHours()).padStart(2, '0');
  const mm = String(d.getUTCMinutes()).padStart(2, '0');
  return `${month} ${day} · ${hh}:${mm} UTC`;
}

const LiveBadge: React.FC<LiveBadgeProps> = ({ status, scheduledAt }) => {
  switch (status) {
    case 'live':
      return (
        <span className="inline-flex items-center gap-1.5 font-display font-bold text-xs tracking-widest text-green-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          LIVE
        </span>
      );
    case 'halftime':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded font-display font-bold text-xs tracking-widest bg-gold/10 text-gold border border-gold/30">
          HALF TIME
        </span>
      );
    case 'finished':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded font-display font-bold text-[10px] tracking-widest bg-slate-700/50 text-slate-400 border border-slate-600/30">
          FULL TIME
        </span>
      );
    case 'postponed':
      return (
        <span className="text-[11px] font-bold tracking-widest text-orange-400 uppercase">
          Postponed
        </span>
      );
    case 'cancelled':
      return (
        <span className="text-[11px] font-bold tracking-widest text-red-400 uppercase line-through">
          Cancelled
        </span>
      );
    case 'scheduled':
    default:
      return (
        <span className="text-[11px] text-slate-500 tabular-nums">
          {scheduledAt ? formatDate(scheduledAt) : '—'}
        </span>
      );
  }
};

export default LiveBadge;
