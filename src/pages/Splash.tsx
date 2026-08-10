import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useUiStore } from "../store/ui";

export function Splash() {
  const navigate = useNavigate();
  const setReady = useUiStore((s) => s.setReady);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("Connecting to orchestrator…");

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        await api.health();
        const status = await api.bootstrap();
        if (!alive) return;
        setProgress(status.progress);
        setMessage(status.message);
        if (status.ready) {
          setReady(true, "Ready");
          navigate("/", { replace: true });
        }
      } catch {
        if (!alive) return;
        setMessage("Waiting for local backend on :8765…");
        setProgress((p) => Math.min(p + 2, 90));
      }
    };
    tick();
    const id = window.setInterval(tick, 800);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [navigate, setReady]);

  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="panel w-full max-w-xl text-center">
        <h1 className="text-4xl tracking-tight">InfluencerForge</h1>
        <p className="muted mt-3">Local-first AI influencer studio</p>
        <div className="mt-8 h-2 overflow-hidden rounded-full bg-[var(--bg2)]">
          <div
            className="h-full bg-[var(--accent)] transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="muted mt-4 text-sm">{message}</p>
      </div>
    </div>
  );
}
