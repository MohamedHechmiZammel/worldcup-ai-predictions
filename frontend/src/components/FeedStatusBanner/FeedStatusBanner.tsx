import { useState, useEffect } from 'react';

interface FeedStatusBannerProps {
  available: boolean;
  lastUpdated?: Date;
}

export default function FeedStatusBanner({ available, lastUpdated }: FeedStatusBannerProps) {
  const [visible, setVisible] = useState(!available);

  useEffect(() => {
    setVisible(!available);
  }, [available]);

  if (available || !visible) return null;

  const timeStr = lastUpdated
    ? lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'unknown';

  return (
    <div className="flex items-center gap-2 bg-yellow-900/50 border border-yellow-700 text-yellow-300 text-sm px-4 py-2 rounded-lg animate-in slide-in-from-top-2 duration-300">
      <span>⚠️</span>
      <span>Live data paused — last updated {timeStr}</span>
      <button
        onClick={() => setVisible(false)}
        className="ml-auto text-yellow-400 hover:text-yellow-200"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}
