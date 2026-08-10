import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, mediaUrl, vaultRevealUrl } from "../api/client";
import { BackLink } from "../components/common/BackLink";
import { ImageLightbox } from "../components/common/ImageLightbox";
import { MediaImage } from "../components/common/MediaImage";
import { PinPrompt } from "../components/common/PinPrompt";
import { StatusBadge } from "../components/common/StatusBadge";
import { IconLock, IconShield } from "../components/common/icons";
import { useVault } from "../hooks/useVault";
import { useVaultReveal } from "../hooks/useVaultReveal";
import type { VaultedGeneration } from "../types";

export function Vault() {
  const { status, setup, unlock, lock } = useVault();
  const reveal = useVaultReveal();
  const [pin, setPin] = useState("");
  const [selected, setSelected] = useState<VaultedGeneration | null>(null);
  const [error, setError] = useState<string | null>(null);

  const unlocked = Boolean(status.data?.unlocked);
  const configured = Boolean(status.data?.configured);
  const pending = status.data?.pending_nsfw ?? 0;

  // Blur cards only while vault is unlocked for browsing.
  const vaulted = useQuery({
    queryKey: ["vault-generations"],
    queryFn: api.listVaultGenerations,
    enabled: configured && unlocked,
    refetchInterval: unlocked ? 4000 : false,
  });
  const vaultItems = unlocked ? (vaulted.data ?? []) : [];
  const selectedIndex = selected ? vaultItems.findIndex((g) => g.id === selected.id) : -1;
  const hasPrev = selectedIndex > 0;
  const hasNext = selectedIndex >= 0 && selectedIndex < vaultItems.length - 1;

  const onSetup = async () => {
    setError(null);
    try {
      await setup.mutateAsync(pin);
      setPin("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Setup failed");
    }
  };

  const onUnlockBrowse = async () => {
    setError(null);
    try {
      await unlock.mutateAsync(pin);
      setPin("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unlock failed");
    }
  };

  const closeLightbox = async () => {
    setSelected(null);
    await reveal.endReveal();
  };

  const openVaulted = (g: VaultedGeneration) => {
    // Always ask PIN for full reveal — even if browsing is unlocked.
    reveal.requestReveal(() => setSelected(g));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackLink fallbackTo="/" label="Back" />
      </div>
      <header>
        <h1 className="text-3xl tracking-tight">Privacy Vault</h1>
        <p className="muted mt-1">
          NSFW posts encrypt into the vault automatically. Locked = cards hidden. Unlocked = blur
          teasers. Opening a post asks for PIN again after you close the viewer.
        </p>
      </header>

      <div className="panel">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`status-badge ${configured ? "tone-ok" : "tone-muted"}`}>
            <IconShield size={13} />
            <span>{configured ? "PIN set" : "No PIN"}</span>
          </span>
          <span className={`status-badge ${unlocked ? "tone-ok" : "tone-wait"}`}>
            <IconLock size={13} />
            <span>{unlocked ? "Browsing unlocked" : "Locked — NSFW hidden"}</span>
          </span>
          {configured && pending > 0 && (
            <span className="status-badge tone-warn" title="NSFW still in cleartext">
              {pending} pending
            </span>
          )}
        </div>
        <div className="field mt-4">
          <label>PIN (min 4 characters)</label>
          <input
            type="password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            autoComplete="off"
          />
        </div>
        {error && <p className="mb-3 text-sm text-[var(--danger)]">{error}</p>}
        <div className="flex flex-wrap gap-3">
          {!configured ? (
            <button className="btn" disabled={pin.length < 4 || setup.isPending} onClick={onSetup}>
              Set PIN
            </button>
          ) : (
            <>
              {!unlocked && (
                <button
                  className="btn"
                  disabled={pin.length < 4 || unlock.isPending}
                  onClick={onUnlockBrowse}
                >
                  Unlock to show blur cards
                </button>
              )}
              {unlocked && (
                <button
                  className="btn secondary"
                  onClick={async () => {
                    await closeLightbox();
                    lock.mutate();
                  }}
                >
                  Lock (hide NSFW)
                </button>
              )}
            </>
          )}
        </div>
        {unlocked && pending > 0 && (
          <p className="muted mt-3 text-sm">
            {pending} NSFW file{pending === 1 ? "" : "s"} still encrypting — refresh in a moment.
          </p>
        )}
        {!unlocked && pending > 0 && (
          <p className="muted mt-3 text-sm">
            {pending} NSFW post{pending === 1 ? "" : "s"} waiting — unlock to encrypt them
            automatically.
          </p>
        )}
      </div>

      {!configured && (
        <div className="panel border-[var(--accent-2)]">
          <p className="text-sm">
            Set a PIN to encrypt NSFW generations. Unlock to browse blurred cards; opening a card
            always asks for the PIN.
          </p>
        </div>
      )}

      {configured && !unlocked && (
        <div className="panel">
          <p className="muted text-sm">
            Vault is locked — NSFW / vaulted posts are hidden. Unlock above to see blurred teasers.
          </p>
        </div>
      )}

      {configured && unlocked && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {vaultItems.map((g) => (
            <button
              key={g.id}
              type="button"
              className="panel gen-card text-left"
              onClick={() => openVaulted(g)}
            >
              <div className="gen-card-media">
                <MediaImage
                  path={g.teaser_path}
                  alt=""
                  className="h-40 w-full rounded-xl object-cover"
                  fallback="Teaser"
                />
                <StatusBadge status="completed" isVaulted overlay />
              </div>
              <p className="gen-card-prompt">{g.user_prompt}</p>
              <span className="gen-card-id">#{g.id}</span>
            </button>
          ))}
          {!vaultItems.length && (
            <p className="muted text-sm">No vaulted generations yet.</p>
          )}
        </div>
      )}

      <PinPrompt
        open={reveal.pinOpen}
        title="Enter PIN to view"
        subtitle="PIN is required every time you open a private post."
        confirmLabel="View post"
        busy={reveal.pinBusy}
        error={reveal.pinError}
        onCancel={reveal.cancelPin}
        onSubmit={reveal.submitPin}
      />

      <ImageLightbox
        open={Boolean(selected) && reveal.viewUnlocked}
        onClose={() => {
          void closeLightbox();
        }}
        title={selected ? `Vaulted #${selected.id}` : ""}
        subtitle={
          selected
            ? `${selected.user_prompt ?? ""}${
                selectedIndex >= 0 ? ` · ${selectedIndex + 1}/${vaultItems.length}` : ""
              }`
            : undefined
        }
        imageSrc={
          selected && reveal.viewUnlocked
            ? `${vaultRevealUrl(selected.id)}?t=view-${selected.id}`
            : selected
              ? mediaUrl(selected.teaser_path)
              : null
        }
        placeholder="Enter PIN to view"
        hasPrev={hasPrev}
        hasNext={hasNext}
        onPrev={() => hasPrev && setSelected(vaultItems[selectedIndex - 1] ?? null)}
        onNext={() => hasNext && setSelected(vaultItems[selectedIndex + 1] ?? null)}
      >
        {selected && (
          <p className="muted text-xs">
            Closing this viewer clears the reveal — opening another post asks for the PIN again.
          </p>
        )}
      </ImageLightbox>
    </div>
  );
}
