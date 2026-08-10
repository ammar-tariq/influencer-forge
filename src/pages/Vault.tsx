import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, mediaUrl, vaultRevealUrl } from "../api/client";
import { ImageLightbox } from "../components/common/ImageLightbox";
import { MediaImage } from "../components/common/MediaImage";
import { useVault } from "../hooks/useVault";
import type { VaultedGeneration } from "../types";

export function Vault() {
  const { status, setup, unlock, lock, vaultPending } = useVault();
  const [pin, setPin] = useState("");
  const [selected, setSelected] = useState<VaultedGeneration | null>(null);
  const [error, setError] = useState<string | null>(null);

  const unlocked = Boolean(status.data?.unlocked);
  const configured = Boolean(status.data?.configured);
  const pending = status.data?.pending_nsfw ?? 0;

  const vaulted = useQuery({
    queryKey: ["vault-generations"],
    queryFn: api.listVaultGenerations,
    enabled: configured,
    refetchInterval: unlocked ? 4000 : false,
  });

  const onSetup = async () => {
    setError(null);
    try {
      await setup.mutateAsync(pin);
      setPin("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Setup failed");
    }
  };

  const onUnlock = async () => {
    setError(null);
    try {
      await unlock.mutateAsync(pin);
      setPin("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unlock failed");
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Privacy Vault</h1>
        <p className="muted mt-1">
          PIN-protected AES-256-GCM storage. NSFW outputs are encrypted; History only keeps blurred
          teasers.
        </p>
      </header>

      <div className="panel">
        <p className="text-sm">
          Configured: {configured ? "yes" : "no"} · Unlocked: {unlocked ? "yes" : "no"}
          {configured && pending > 0 ? ` · ${pending} NSFW still in cleartext History` : ""}
        </p>
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
                <button className="btn" disabled={pin.length < 4 || unlock.isPending} onClick={onUnlock}>
                  Unlock
                </button>
              )}
              {unlocked && (
                <button className="btn secondary" onClick={() => lock.mutate()}>
                  Lock
                </button>
              )}
              {unlocked && pending > 0 && (
                <button
                  className="btn"
                  disabled={vaultPending.isPending}
                  onClick={() => vaultPending.mutate()}
                >
                  {vaultPending.isPending
                    ? "Vaulting…"
                    : `Vault ${pending} pending NSFW`}
                </button>
              )}
            </>
          )}
        </div>
        {vaultPending.data && (
          <p className="muted mt-3 text-sm">
            Moved {vaultPending.data.count} into the vault
            {vaultPending.data.errors.length
              ? ` · ${vaultPending.data.errors.length} failed`
              : ""}
          </p>
        )}
      </div>

      {!configured && (
        <div className="panel border-[var(--accent-2)]">
          <p className="text-sm">
            Set a PIN to encrypt NSFW generations. With the vault unlocked, new NSFW jobs auto-vault
            and cleartext files are deleted.
          </p>
        </div>
      )}

      {configured && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(vaulted.data ?? []).map((g) => (
            <button key={g.id} className="panel text-left" onClick={() => setSelected(g)}>
              <MediaImage
                path={g.teaser_path}
                alt=""
                className="mb-3 h-40 w-full rounded-xl object-cover"
                fallback="Teaser"
              />
              <div className="font-semibold">#{g.id} · vaulted</div>
              <p className="muted mt-1 line-clamp-2 text-sm">{g.user_prompt}</p>
            </button>
          ))}
          {!vaulted.data?.length && (
            <p className="muted text-sm">No vaulted generations yet.</p>
          )}
        </div>
      )}

      <ImageLightbox
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected ? `Vaulted #${selected.id}` : ""}
        subtitle={selected?.user_prompt}
        imageSrc={
          selected
            ? unlocked
              ? `${vaultRevealUrl(selected.id)}?t=${Date.now()}`
              : mediaUrl(selected.teaser_path)
            : null
        }
        placeholder={unlocked ? "Image unavailable" : "Unlock the vault to view the full image"}
      >
        {selected && !unlocked && (
          <p className="muted text-sm">Showing blurred teaser only — unlock above to decrypt.</p>
        )}
        {selected && unlocked && (
          <p className="muted text-xs">
            Cleartext is not stored — this view is decrypted in memory/cache while unlocked.
          </p>
        )}
      </ImageLightbox>
    </div>
  );
}
