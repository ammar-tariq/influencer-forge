import { useEffect } from "react";
import { api } from "../api/client";

/** Listen for system-tray pause/resume events (Tauri desktop only). */
export function useTrayQueueControls() {
  useEffect(() => {
    let cancelled = false;
    const unsubs: Array<() => void> = [];

    void (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        if (cancelled) return;
        const offPause = await listen("tray-queue-pause", () => {
          void api.pauseQueue();
        });
        const offResume = await listen("tray-queue-resume", () => {
          void api.resumeQueue();
        });
        unsubs.push(offPause, offResume);
      } catch {
        // Browser / vitest — no Tauri event bridge.
      }
    })();

    return () => {
      cancelled = true;
      for (const off of unsubs) off();
    };
  }, []);
}
