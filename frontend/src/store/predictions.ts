import { create } from 'zustand';
import type { Prediction, LiveEvent, LiveMatchStateData } from '../types';

interface PredictionsState {
  predictions: Record<number, Prediction>;
  liveEvents: Record<number, LiveEvent[]>;
  feedStatus: Record<number, boolean>;
  liveMatchState: Record<number, LiveMatchStateData>;
  updatePrediction: (matchId: number, prediction: Prediction) => void;
  addLiveEvent: (matchId: number, event: LiveEvent) => void;
  setFeedStatus: (matchId: number, available: boolean) => void;
  setMatchState: (matchId: number, state: LiveMatchStateData) => void;
}

export const usePredictionsStore = create<PredictionsState>((set) => ({
  predictions: {},
  liveEvents: {},
  feedStatus: {},
  liveMatchState: {},
  updatePrediction: (matchId, prediction) =>
    set((state) => ({ predictions: { ...state.predictions, [matchId]: prediction } })),
  addLiveEvent: (matchId, event) =>
    set((state) => ({
      liveEvents: {
        ...state.liveEvents,
        [matchId]: [event, ...(state.liveEvents[matchId] ?? [])],
      },
    })),
  setFeedStatus: (matchId, available) =>
    set((state) => ({ feedStatus: { ...state.feedStatus, [matchId]: available } })),
  setMatchState: (matchId, matchState) =>
    set((state) => ({ liveMatchState: { ...state.liveMatchState, [matchId]: matchState } })),
}));
