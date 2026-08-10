import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, mediaUrl, vaultRevealUrl } from "../api/client";
import { GenerationCard } from "../components/common/GenerationCard";
import { ImageLightbox } from "../components/common/ImageLightbox";
import { StatusBadge } from "../components/common/StatusBadge";
import type { Generation } from "../types";

export function History() {
  const qc = useQueryClient();
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

  const vault = useMutation({
    mutationFn: (id: number) => api.vaultGeneration(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["generations"] });
      qc.invalidateQueries({ queryKey: ["vault-status"] });
      qc.invalidateQueries({ queryKey: ["vault-generations"] });
      setSelected((prev) =>
        prev && prev.id === id
          ? { ...prev, is_vaulted: true, output_path: null, output_thumbnail_path: null }
          : prev,
      );
    },
  });

  const items = useMemo(() => generations.data ?? [], [generations.data]);
  const unlocked = Boolean(vaultStatus.data?.unlocked);
  const pendingNsfw = vaultStatus.data?.pending_nsfw ?? 0;

  const cardPath = (g: Generation) =>
    g.is_vaulted
      ? g.teaser_path
      : (g.output_thumbnail_path ?? g.output_path ?? g.teaser_path);

  const detailSrc = selected
    ? selected.is_vaulted
      ? unlocked
        ? vaultRevealUrl(selected.id)
        : mediaUrl(selected.teaser_path)
      : (mediaUrl(selected.output_path) ??
        mediaUrl(selected.output_thumbnail_path) ??
        mediaUrl(selected.teaser_path))
    : undefined;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Library</h1>
        <p className="muted mt-1">
          All generated content
          {influencerId !== ""
            ? ` for ${influencers.data?.find((i) => i.id === influencerId)?.name ?? `#${influencerId}`}`
            : ""}
          . Filter by influencer or open one from{" "}
          <Link className="underline" to="/influencers">
            Influencers
          </Link>
          .
        </p>
      </header>

      {pendingNsfw > 0 && (
        <div className="panel border-[var(--accent-2)]">
          <p className="text-sm">
            {pendingNsfw} NSFW generation{pendingNsfw === 1 ? "" : "s"} still in cleartext.{" "}
            <Link className="underline" to="/vault">
              Unlock the vault
            </Link>{" "}
            and use “Vault pending NSFW”.
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
            onClick={() => setSelected(g)}
          />
        ))}
      </div>

      <ImageLightbox
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected ? `Generation #${selected.id}` : ""}
        subtitle={
          selected ? `Seed ${selected.seed ?? "—"} · ${selected.model_used}` : undefined
        }
        imageSrc={
          selected && detailSrc
            ? selected.is_vaulted && unlocked
              ? `${detailSrc}?t=${Date.now()}`
              : detailSrc
            : null
        }
        placeholder={
          selected?.is_vaulted && !unlocked
            ? "Unlock the vault to view full image"
            : `${selected?.status ?? ""}${selected?.error_message ? ` — ${selected.error_message}` : ""}`
        }
      >
        {selected && (
          <>
            <StatusBadge
              status={selected.status}
              isVaulted={selected.is_vaulted}
              isNsfw={selected.is_nsfw}
            />
            {selected.is_vaulted && !unlocked && (
              <p className="muted text-sm">
                Showing blurred teaser only.{" "}
                <Link className="underline" to="/vault">
                  Open Vault
                </Link>
              </p>
            )}
            <p className="line-clamp-4 text-sm">{selected.expanded_prompt}</p>
            <div className="flex flex-wrap gap-3">
              <button className="btn" onClick={() => regenerate.mutate(selected.id)}>
                Regenerate
              </button>
              {!selected.is_vaulted && selected.output_path && (
                <button
                  className="btn secondary"
                  disabled={!vaultStatus.data?.unlocked}
                  onClick={() => vault.mutate(selected.id)}
                >
                  Move to vault
                </button>
              )}
              {selected.is_vaulted && (
                <Link className="btn secondary" to="/vault">
                  Open in Vault
                </Link>
              )}
              {detailSrc && !selected.is_vaulted && (
                <a className="btn secondary" href={detailSrc} target="_blank" rel="noreferrer">
                  Open in new tab
                </a>
              )}
            </div>
            {!selected.is_vaulted && selected.output_path && !vaultStatus.data?.unlocked && (
              <p className="muted text-xs">Unlock the vault (Vault page) before moving items.</p>
            )}
          </>
        )}
      </ImageLightbox>
    </div>
  );
}
