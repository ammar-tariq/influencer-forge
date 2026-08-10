import { useQueue } from "../../hooks/useQueue";

export function QueueStatusChip() {
  const { data } = useQueue();
  if (!data) return <div className="muted text-xs">Queue…</div>;
  return (
    <div className="rounded-xl border border-[var(--line)] px-3 py-2 text-xs">
      <div className="font-semibold text-[var(--accent)]">Queue</div>
      <div className="muted mt-1">
        {data.paused ? "Paused · " : ""}
        {data.pending} pending · {data.processing} active
      </div>
    </div>
  );
}
