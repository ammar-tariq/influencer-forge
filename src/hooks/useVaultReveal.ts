import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

/**
 * Per-lightbox reveal session for vaulted/NSFW posts.
 * - Vault unlock (browse) can stay on so blur cards remain visible.
 * - Opening a post always requires PIN; closing the lightbox ends the view session
 *   so the next open asks again.
 */
export function useVaultReveal() {
  const qc = useQueryClient();
  const [viewUnlocked, setViewUnlocked] = useState(false);
  const [pinOpen, setPinOpen] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);
  const [pinBusy, setPinBusy] = useState(false);
  const [pendingOpen, setPendingOpen] = useState<(() => void) | null>(null);

  const requestReveal = useCallback((onUnlocked: () => void) => {
    setPinError(null);
    setPendingOpen(() => onUnlocked);
    setPinOpen(true);
  }, []);

  const cancelPin = useCallback(() => {
    setPinOpen(false);
    setPinError(null);
    setPendingOpen(null);
    setPinBusy(false);
  }, []);

  const submitPin = useCallback(
    async (pin: string) => {
      setPinBusy(true);
      setPinError(null);
      try {
        await api.vaultUnlock(pin);
        setViewUnlocked(true);
        setPinOpen(false);
        await qc.invalidateQueries({ queryKey: ["vault-status"] });
        await qc.invalidateQueries({ queryKey: ["vault-generations"] });
        const cb = pendingOpen;
        setPendingOpen(null);
        cb?.();
      } catch (e) {
        setPinError(e instanceof Error ? e.message : "Incorrect PIN");
      } finally {
        setPinBusy(false);
      }
    },
    [pendingOpen, qc],
  );

  const endReveal = useCallback(async () => {
    setViewUnlocked(false);
    try {
      await api.vaultEndView();
    } catch {
      // best-effort cache wipe
    }
  }, []);

  return {
    viewUnlocked,
    pinOpen,
    pinError,
    pinBusy,
    requestReveal,
    submitPin,
    cancelPin,
    endReveal,
  };
}
