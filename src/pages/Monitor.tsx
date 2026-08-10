import { useMutation, useQuery } from "@tanstack/react-query";
import { useSystemStats } from "../hooks/useSystemStats";
import { api } from "../api/client";

export function Monitor() {
  const { data } = useSystemStats();
  const comfy = useQuery({
    queryKey: ["comfy-status"],
    queryFn: api.comfyStatus,
    refetchInterval: 3000,
  });
  const pause = useMutation({ mutationFn: api.pauseQueue });
  const resume = useMutation({ mutationFn: api.resumeQueue });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">System monitor</h1>
        <p className="muted mt-1">Live CPU/RAM, queue pressure, and ComfyUI health.</p>
      </header>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="panel">
          <div className="muted text-sm">CPU</div>
          <div className="mt-2 text-3xl">{data?.cpu_percent?.toFixed(0) ?? "—"}%</div>
        </div>
        <div className="panel">
          <div className="muted text-sm">RAM</div>
          <div className="mt-2 text-3xl">{data?.ram_percent?.toFixed(0) ?? "—"}%</div>
          <div className="muted mt-1 text-xs">
            {data ? `${data.ram_used_gb}/${data.ram_total_gb} GB` : ""}
          </div>
        </div>
        <div className="panel">
          <div className="muted text-sm">Queue</div>
          <div className="mt-2 text-3xl">
            {data ? `${data.queue_pending}/${data.queue_processing}` : "—"}
          </div>
        </div>
      </div>
      <div className="panel">
        <h2 className="text-lg">ComfyUI</h2>
        <p className="muted mt-2 text-sm">
          enabled={String(comfy.data?.enabled ?? false)} · healthy=
          {String(comfy.data?.healthy ?? false)} · process=
          {String(comfy.data?.process_running ?? false)}
        </p>
        <p className="muted mt-1 text-xs">{comfy.data?.url}</p>
      </div>
      <div className="panel flex gap-3">
        <button className="btn secondary" onClick={() => pause.mutate()}>
          Pause queue
        </button>
        <button className="btn" onClick={() => resume.mutate()}>
          Resume queue
        </button>
      </div>
    </div>
  );
}
