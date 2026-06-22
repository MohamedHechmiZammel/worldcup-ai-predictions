import { create } from 'zustand';
import type { Prediction, LiveEvent } from '../types';

interface PredictionsState {
  predictions: Record<number, Prediction>;
  liveEvents: Record<number, LiveEvent[]>;
  feedStatus: Record<number, boolean>;
  updatePrediction: (matchId: number, prediction: Prediction) => void;
  addLiveEvent: (matchId: number, event: LiveEvent) => void;
  setFeedStatus: (matchId: number, available: boolean) => void;
}

export const usePredictionsStore = create<PredictionsState>((set) => ({
  predictions: {},
  liveEvents: {},
  feedStatus: {},
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
}));
