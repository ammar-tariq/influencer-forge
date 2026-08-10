import {
  IconCheck,
  IconClock,
  IconFlame,
  IconLock,
  IconSpinner,
  IconX,
} from "./icons";

type Tone = "ok" | "busy" | "wait" | "danger" | "warn" | "vault" | "muted";

const STATUS_MAP: Record<
  string,
  { label: string; tone: Tone; Icon: typeof IconCheck; spin?: boolean }
> = {
  completed: { label: "Done", tone: "ok", Icon: IconCheck },
  processing: { label: "Working", tone: "busy", Icon: IconSpinner, spin: true },
  queued: { label: "Queued", tone: "wait", Icon: IconClock },
  pending: { label: "Queued", tone: "wait", Icon: IconClock },
  failed: { label: "Failed", tone: "danger", Icon: IconX },
};

type Props = {
  status?: string | null;
  isVaulted?: boolean;
  isNsfw?: boolean;
  /** icon-only corner chip (title still set for a11y) */
  overlay?: boolean;
};

export function StatusBadge({ status, isVaulted, isNsfw, overlay }: Props) {
  const key = (status || "").toLowerCase();
  const mapped = STATUS_MAP[key] ?? {
    label: status || "Unknown",
    tone: "muted" as Tone,
    Icon: IconClock,
  };
  const { label, tone, Icon, spin } = mapped;

  return (
    <span className={`status-row ${overlay ? "status-row-overlay" : ""}`}>
      <span className={`status-badge tone-${tone}`} title={label}>
        <Icon size={13} className={spin ? "spin" : undefined} />
        {!overlay && <span>{label}</span>}
        {overlay && <span className="sr-only">{label}</span>}
      </span>
      {isVaulted && (
        <span className="status-badge tone-vault" title="In vault">
          <IconLock size={13} />
          {!overlay && <span>Vault</span>}
          {overlay && <span className="sr-only">In vault</span>}
        </span>
      )}
      {isNsfw && !isVaulted && (
        <span className="status-badge tone-warn" title="NSFW">
          <IconFlame size={13} />
          {!overlay && <span>NSFW</span>}
          {overlay && <span className="sr-only">NSFW</span>}
        </span>
      )}
    </span>
  );
}

type FaceLockProps = {
  faceLock?: string | null;
  overlay?: boolean;
};

export function FaceLockBadge({ faceLock, overlay }: FaceLockProps) {
  if (!faceLock || faceLock === "none") {
    return (
      <span className="status-badge tone-muted" title="Face not locked">
        <IconClock size={13} />
        {!overlay && <span>No lock</span>}
        {overlay && <span className="sr-only">Face not locked</span>}
      </span>
    );
  }
  return (
    <span className="status-badge tone-ok" title={`Face lock: ${faceLock.replace("_", " ")}`}>
      <IconCheck size={13} />
      {!overlay && <span>Face locked</span>}
      {overlay && <span className="sr-only">Face locked</span>}
    </span>
  );
}
