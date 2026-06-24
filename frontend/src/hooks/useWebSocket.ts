import { useRef, useState, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { Prediction, LiveEvent, LiveMatchStateData, WSMessage } from '../types';
import { usePredictionsStore } from '../store/predictions';

type ConnectionState = 'connecting' | 'connected' | 'disconnected';

export function useWebSocket(matchId: number) {
  const queryClient = useQueryClient();
  const updatePrediction = usePredictionsStore(s => s.updatePrediction);
  const addLiveEvent = usePredictionsStore(s => s.addLiveEvent);
  const setFeedStatus = usePredictionsStore(s => s.setFeedStatus);
  const setMatchState = usePredictionsStore(s => s.setMatchState);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectDelayRef = useRef(1000);  // starts at 1s
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');

  const handleMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case 'prediction_update':
        if (msg.payload) {
          updatePrediction(matchId, msg.payload as Prediction);
        }
        break;
      case 'live_event':
        if (msg.payload) {
          addLiveEvent(matchId, msg.payload as LiveEvent);
        }
        break;
      case 'match_state_update':
        if (msg.payload) {
          setMatchState(matchId, msg.payload as LiveMatchStateData);
        }
        break;
      case 'match_status_change':
        // Invalidate both the list and the individual match so REST data refreshes
        queryClient.invalidateQueries({ queryKey: ['matches'] });
        queryClient.invalidateQueries({ queryKey: ['match', matchId] });
        break;
      case 'accuracy_update':
        queryClient.invalidateQueries({ queryKey: ['accuracy'] });
        break;
      case 'feed_status':
        if (msg.payload) {
          const { available } = msg.payload as { available: boolean };
          setFeedStatus(matchId, available);
        }
        break;
      case 'ping':
        // Respond with pong
        wsRef.current?.send(JSON.stringify({ type: 'pong' }));
        break;
    }
  }, [matchId, queryClient, updatePrediction, addLiveEvent, setFeedStatus, setMatchState]);

  // Forward-declare scheduleReconnect so connect can reference it
  const scheduleReconnectRef = useRef<() => void>(() => undefined);

  const connect = useCallback(() => {
    let base = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
    // Auto-convert http(s) → ws(s) so a misconfigured env var doesn't throw
    base = base.replace(/^https:\/\//, 'wss://').replace(/^http:\/\//, 'ws://');
    const wsUrl = `${base}/ws/matches/${matchId}`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch {
      // Invalid URL (e.g. wrong scheme) — schedule reconnect instead of crashing
      scheduleReconnectRef.current();
      return;
    }
    wsRef.current = ws;
    setConnectionState('connecting');

    ws.onopen = () => {
      setConnectionState('connected');
      reconnectDelayRef.current = 1000;  // reset backoff on successful connect
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data as string);
        handleMessage(msg);
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnectionState('disconnected');
      scheduleReconnectRef.current();
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [matchId, handleMessage]);

  // Exponential backoff reconnect: 1s → 2s → 4s → ... → 30s max
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    const delay = reconnectDelayRef.current;
    reconnectDelayRef.current = Math.min(delay * 2, 30_000);
    reconnectTimeoutRef.current = window.setTimeout(connect, delay);
  }, [connect]);

  // Keep the ref in sync so the ws.onclose closure always has the latest version
  useEffect(() => {
    scheduleReconnectRef.current = scheduleReconnect;
  }, [scheduleReconnect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connectionState };
}
