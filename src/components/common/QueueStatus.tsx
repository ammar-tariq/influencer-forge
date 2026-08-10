import { useQueue } from "../../hooks/useQueue";
import { IconClock, IconSpinner } from "./icons";

export function QueueStatusChip() {
  const { data } = useQueue();
  if (!data) {
    return (
      <div className="queue-chip rounded-xl border border-[var(--line)] px-3 py-2">
        <span className="status-badge tone-wait">
          <IconSpinner size={13} className="spin" />
          <span>Queue</span>
        </span>
      </div>
    );
  }

  const busy = data.processing > 0;
  const paused = data.paused;

  return (
    <div className="queue-chip rounded-xl border border-[var(--line)] px-3 py-2">
      <div className="queue-chip-row">
        <span className={`status-badge ${paused ? "tone-warn" : busy ? "tone-busy" : "tone-ok"}`}>
          {busy ? <IconSpinner size={13} className="spin" /> : <IconClock size={13} />}
          <span>{paused ? "Paused" : busy ? "Active" : "Idle"}</span>
        </span>
      </div>
      <div className="queue-chip-row">
        <span className="queue-stat" title="Waiting in queue">
          <IconClock size={12} />
          {data.pending}
        </span>
        <span className="queue-stat" title="Generating now">
          <IconSpinner size={12} className={busy ? "spin" : undefined} />
          {data.processing}
        </span>
      </div>
    </div>
  );
}
