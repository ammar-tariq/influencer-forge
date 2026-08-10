import { create } from "zustand";

interface UiState {
  ready: boolean;
  backendMessage: string;
  setReady: (ready: boolean, message?: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  ready: false,
  backendMessage: "Starting…",
  setReady: (ready, message) =>
    set({ ready, backendMessage: message ?? (ready ? "Ready" : "Starting…") }),
}));
