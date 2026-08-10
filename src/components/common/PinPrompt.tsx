import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

type Props = {
  open: boolean;
  title?: string;
  subtitle?: string;
  confirmLabel?: string;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onSubmit: (pin: string) => void;
};

/** Modal PIN entry for vault unlock / NSFW reveal. */
export function PinPrompt({
  open,
  title = "Enter vault PIN",
  subtitle = "Required to view this private post.",
  confirmLabel = "Unlock",
  busy = false,
  error = null,
  onCancel,
  onSubmit,
}: Props) {
  const [pin, setPin] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) {
      setPin("");
      return;
    }
    const t = window.setTimeout(() => inputRef.current?.focus(), 50);
    return () => window.clearTimeout(t);
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className="lightbox-root"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onCancel}
    >
      <div
        className="panel"
        style={{ width: "min(420px, 100%)", margin: "1rem" }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl tracking-tight">{title}</h2>
        {subtitle && <p className="muted mt-2 text-sm">{subtitle}</p>}
        <div className="field mt-4">
          <label>PIN</label>
          <input
            ref={inputRef}
            type="password"
            value={pin}
            autoComplete="off"
            disabled={busy}
            onChange={(e) => setPin(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && pin.length >= 4 && !busy) onSubmit(pin);
            }}
          />
        </div>
        {error && <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn"
            disabled={pin.length < 4 || busy}
            onClick={() => onSubmit(pin)}
          >
            {busy ? "Checking…" : confirmLabel}
          </button>
          <button type="button" className="btn secondary" disabled={busy} onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
