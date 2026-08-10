import { useState } from "react";
import { PinPrompt } from "./PinPrompt";
import { IconLock, IconShield } from "./icons";
import { useVault } from "../../hooks/useVault";

/**
 * Sidebar control: off = vault locked (NSFW hidden), on = browsing unlocked (blur cards).
 * Turning on always asks for PIN (setup if first time).
 */
export function VaultToggle() {
  const { status, setup, unlock, lock } = useVault();
  const [pinOpen, setPinOpen] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const configured = Boolean(status.data?.configured);
  const unlocked = Boolean(status.data?.unlocked);
  const pending = status.data?.pending_nsfw ?? 0;

  const onToggle = () => {
    if (unlocked) {
      lock.mutate();
      return;
    }
    setPinError(null);
    setPinOpen(true);
  };

  const onSubmitPin = async (pin: string) => {
    setBusy(true);
    setPinError(null);
    try {
      if (!configured) {
        await setup.mutateAsync(pin);
      } else {
        await unlock.mutateAsync(pin);
      }
      setPinOpen(false);
    } catch (e) {
      setPinError(e instanceof Error ? e.message : "PIN failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="vault-toggle">
      <div className="vault-toggle-row">
        <div className="vault-toggle-label">
          <IconShield size={16} />
          <div>
            <div className="text-sm font-medium text-[var(--ink)]">Privacy vault</div>
            <p className="muted text-xs">
              {unlocked ? "NSFW teasers visible" : "NSFW hidden"}
              {pending > 0 ? ` · ${pending} pending` : ""}
            </p>
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={unlocked}
          aria-label={unlocked ? "Lock privacy vault" : "Unlock privacy vault"}
          className={`vault-switch ${unlocked ? "on" : ""}`}
          disabled={status.isLoading || lock.isPending || busy}
          onClick={onToggle}
        >
          <span className="vault-switch-thumb">
            <IconLock size={10} />
          </span>
        </button>
      </div>

      <PinPrompt
        open={pinOpen}
        title={configured ? "Unlock vault" : "Set vault PIN"}
        subtitle={
          configured
            ? "Enter your PIN to show blurred NSFW teasers. Opening a post will ask again."
            : "Choose a PIN (min 4 characters). NSFW posts will encrypt automatically."
        }
        confirmLabel={configured ? "Unlock" : "Set PIN"}
        busy={busy}
        error={pinError}
        onCancel={() => {
          setPinOpen(false);
          setPinError(null);
        }}
        onSubmit={onSubmitPin}
      />
    </div>
  );
}
