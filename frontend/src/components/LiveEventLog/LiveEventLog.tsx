import { useEffect, useRef } from 'react';
import type { LiveEvent } from '../../types';

interface LiveEventLogProps {
  events: LiveEvent[];  // newest at top (already sorted by parent)
}

const EVENT_ICONS: Record<string, string> = {
  goal: '⚽',
  yellow_card: '🟨',
  red_card: '🟥',
  substitution: '🔄',
  halftime: '⏸️',
  fulltime: '🏁',
};

export default function LiveEventLog({ events }: LiveEventLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top when new event arrives
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events.length]);

  if (events.length === 0) {
    return (
      <div className="text-gray-500 text-sm italic text-center py-4">
        No events yet
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="max-h-64 overflow-y-auto space-y-2 scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-gray-600"
    >
      {events.map(event => (
        <div key={event.id} className="flex items-start gap-3 p-2 rounded bg-gray-800/50">
          <span className="text-lg">{EVENT_ICONS[event.event_type] ?? '•'}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-white text-sm font-medium">
                {event.player_name ?? event.event_type.replace('_', ' ')}
              </span>
              <span className="text-xs text-gray-400">{event.minute}'</span>
            </div>
            <div className="text-xs text-gray-500">
              {event.home_score_after} – {event.away_score_after}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
