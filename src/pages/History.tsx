import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, mediaUrl, vaultRevealUrl } from "../api/client";
import { BackLink } from "../components/common/BackLink";
import { GenerationCard } from "../components/common/GenerationCard";
import { ImageLightbox } from "../components/common/ImageLightbox";
import { PinPrompt } from "../components/common/PinPrompt";
import { StatusBadge } from "../components/common/StatusBadge";
import { useVaultReveal } from "../hooks/useVaultReveal";
import type { Generation } from "../types";

export function History() {
  const qc = useQueryClient();
  const reveal = useVaultReveal();
  const [params, setParams] = useSearchParams();
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const vaultStatus = useQuery({ queryKey: ["vault-status"], queryFn: api.vaultStatus });
  const initialInf = params.get("influencer");
  const [influencerId, setInfluencerId] = useState<number | "">(
    initialInf && Number(initialInf) ? Number(initialInf) : "",
  );
  const [nsfw, setNsfw] = useState<"all" | "sfw" | "nsfw">("all");
  const [selected, setSelected] = useState<Generation | null>(null);

  useEffect(() => {
    const fromUrl = params.get("influencer");
    if (fromUrl && Number(fromUrl)) {
      setInfluencerId(Number(fromUrl));
    }
  }, [params]);

  const generations = useQuery({
    queryKey: ["generations", influencerId, nsfw],
    queryFn: () =>
      api.listGenerations({
        influencer_id: influencerId === "" ? undefined : Number(influencerId),
        is_nsfw: nsfw === "all" ? undefined : nsfw === "nsfw",
      }),
    refetchInterval: 2000,
  });

  const regenerate = useMutation({
    mutationFn: (id: number) => api.regenerate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["generations"] }),
  });

  const items = useMemo(() => generations.data ?? [], [generations.data]);
  const browseUnlocked = Boolean(vaultStatus.data?.unlocked);
  const pendingNsfw = vaultStatus.data?.pending_nsfw ?? 0;
  const selectedIndex = selected ? items.findIndex((g) => g.id === selected.id) : -1;
  const hasPrev = selectedIndex > 0;
  const hasNext = selectedIndex >= 0 && selectedIndex < items.length - 1;

  const cardPath = (g: Generation) =>
    g.is_vaulted
      ? g.teaser_path
      : (g.output_thumbnail_path ?? g.output_path ?? g.teaser_path);

  const openPost = (g: Generation) => {
    if (g.is_vaulted) {
      reveal.requestReveal(() => setSelected(g));
      return;
    }
    setSelected(g);
  };

  const goAdjacent = (g: Generation | undefined) => {
    if (!g) return;
    if (g.is_vaulted && !reveal.viewUnlocked) {
      reveal.requestReveal(() => setSelected(g));
      return;
    }
    setSelected(g);
  };

  const closeLightbox = async () => {
    setSelected(null);
    if (reveal.viewUnlocked) await reveal.endReveal();
  };

  const detailSrc = selected
    ? selected.is_vaulted
      ? reveal.viewUnlocked
        ? vaultRevealUrl(selected.id)
        : mediaUrl(selected.teaser_path)
      : (mediaUrl(selected.output_path) ??
        mediaUrl(selected.output_thumbnail_path) ??
        mediaUrl(selected.teaser_path))
    : undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackLink
          fallbackTo={influencerId !== "" ? `/influencers/${influencerId}` : "/influencers"}
          label="Back"
        />
      </div>
      <header>
        <h1 className="text-3xl tracking-tight">Library</h1>
        <p className="muted mt-1">
          Generated posts
          {influencerId !== ""
            ? ` for ${influencers.data?.find((i) => i.id === influencerId)?.name ?? `#${influencerId}`}`
            : ""}
          .
        </p>
      </header>

      {pendingNsfw > 0 && (
        <div className="panel border-[var(--accent-2)]">
          <p className="text-sm">
            {pendingNsfw} NSFW generation{pendingNsfw === 1 ? "" : "s"} waiting to encrypt.{" "}
            <Link className="underline" to="/vault">
              Unlock the vault
            </Link>{" "}
            — they move in automatically.
          </p>
        </div>
      )}

      <div className="panel flex flex-wrap gap-3">
        <select
          value={influencerId}
          onChange={(e) => {
            const next = e.target.value ? Number(e.target.value) : "";
            setInfluencerId(next);
            if (next === "") {
              params.delete("influencer");
            } else {
              params.set("influencer", String(next));
            }
            setParams(params, { replace: true });
          }}
        >
          <option value="">All influencers</option>
          {(influencers.data ?? []).map((inf) => (
            <option key={inf.id} value={inf.id}>
              {inf.name}
            </option>
          ))}
        </select>
        {influencerId !== "" && (
          <Link className="btn secondary" to={`/influencers/${influencerId}`}>
            Influencer details
          </Link>
        )}
        <select value={nsfw} onChange={(e) => setNsfw(e.target.value as typeof nsfw)}>
          <option value="all">SFW + NSFW</option>
          <option value="sfw">SFW only</option>
          <option value="nsfw">NSFW only</option>
        </select>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((g) => (
          <GenerationCard
            key={g.id}
            generation={g}
            imagePath={cardPath(g)}
            onClick={() => openPost(g)}
          />
        ))}
      </div>

      <PinPrompt
        open={reveal.pinOpen}
        title="Enter PIN to view"
        subtitle="Vaulted posts always require your PIN."
        confirmLabel="View post"
        busy={reveal.pinBusy}
        error={reveal.pinError}
        onCancel={reveal.cancelPin}
        onSubmit={reveal.submitPin}
      />

      <ImageLightbox
        open={Boolean(selected) && (!selected?.is_vaulted || reveal.viewUnlocked)}
        onClose={() => {
          void closeLightbox();
        }}
        title={selected ? `Generation #${selected.id}` : ""}
        subtitle={
          selected
            ? `Seed ${selected.seed ?? "—"} · ${selected.model_used}${
                selectedIndex >= 0 ? ` · ${selectedIndex + 1}/${items.length}` : ""
              }`
            : undefined
        }
        imageSrc={
          selected && detailSrc
            ? selected.is_vaulted
              ? `${detailSrc}?t=${selected.id}-${reveal.viewUnlocked ? "1" : "0"}`
              : detailSrc
            : null
        }
        placeholder={`${selected?.status ?? ""}${selected?.error_message ? ` — ${selected.error_message}` : ""}`}
        hasPrev={hasPrev}
        hasNext={hasNext}
        onPrev={() => hasPrev && goAdjacent(items[selectedIndex - 1])}
        onNext={() => hasNext && goAdjacent(items[selectedIndex + 1])}
      >
        {selected && (
          <>
            <StatusBadge
              status={selected.status}
              isVaulted={selected.is_vaulted}
              isNsfw={selected.is_nsfw}
            />
            <p className="line-clamp-4 text-sm">{selected.expanded_prompt}</p>
            <div className="flex flex-wrap gap-3">
              <button className="btn" onClick={() => regenerate.mutate(selected.id)}>
                Regenerate
              </button>
              {selected.is_vaulted && (
                <Link className="btn secondary" to="/vault">
                  Open in Vault
                </Link>
              )}
              {selected.is_nsfw && !selected.is_vaulted && (
                <p className="muted text-xs">
                  NSFW auto-vaults when the vault is unlocked
                  {browseUnlocked ? "…" : " — unlock on the Vault page to encrypt pending items."}
                </p>
              )}
              {detailSrc && !selected.is_vaulted && (
                <a className="btn secondary" href={detailSrc} target="_blank" rel="noreferrer">
                  Open in new tab
                </a>
              )}
            </div>
          </>
        )}
      </ImageLightbox>
    </div>
  );
}
