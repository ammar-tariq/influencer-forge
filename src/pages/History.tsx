import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, mediaUrl, vaultRevealUrl } from "../api/client";
import { MediaImage } from "../components/common/MediaImage";
import type { Generation } from "../types";

export function History() {
  const qc = useQueryClient();
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const vaultStatus = useQuery({ queryKey: ["vault-status"], queryFn: api.vaultStatus });
  const [influencerId, setInfluencerId] = useState<number | "">("");
  const [nsfw, setNsfw] = useState<"all" | "sfw" | "nsfw">("all");
  const [selected, setSelected] = useState<Generation | null>(null);

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
        <h1 className="text-3xl tracking-tight">History</h1>
        <p className="muted mt-1">Browse generations, inspect seeds, regenerate.</p>
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
          onChange={(e) => setInfluencerId(e.target.value ? Number(e.target.value) : "")}
        >
          <option value="">All influencers</option>
          {(influencers.data ?? []).map((inf) => (
            <option key={inf.id} value={inf.id}>
              {inf.name}
            </option>
          ))}
        </select>
        <select value={nsfw} onChange={(e) => setNsfw(e.target.value as typeof nsfw)}>
          <option value="all">SFW + NSFW</option>
          <option value="sfw">SFW only</option>
          <option value="nsfw">NSFW only</option>
        </select>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((g) => (
          <button key={g.id} className="panel text-left" onClick={() => setSelected(g)}>
            <MediaImage
              path={cardPath(g)}
              alt=""
              className="mb-3 h-40 w-full rounded-xl object-cover"
              fallback={g.status}
            />
            <div className="font-semibold">
              #{g.id} · {g.status}
              {g.is_vaulted ? " · In vault" : ""}
              {g.is_nsfw && !g.is_vaulted ? " · NSFW" : ""}
            </div>
            <p className="muted mt-1 line-clamp-2 text-sm">{g.user_prompt}</p>
          </button>
        ))}
      </div>

      {selected && (
        <div className="panel">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl">Generation #{selected.id}</h2>
              <p className="muted mt-1 text-sm">
                Seed {selected.seed ?? "—"} · {selected.model_used}
                {selected.is_vaulted ? " · vaulted" : ""}
              </p>
            </div>
            <button className="btn secondary" onClick={() => setSelected(null)}>
              Close
            </button>
          </div>
          {detailSrc ? (
            <a href={detailSrc} target="_blank" rel="noreferrer">
              <img
                key={detailSrc}
                src={selected.is_vaulted && unlocked ? `${detailSrc}?t=${Date.now()}` : detailSrc}
                alt={`Generation ${selected.id}`}
                className="mt-4 max-h-[70vh] w-full rounded-xl object-contain bg-[var(--bg2)]"
              />
            </a>
          ) : (
            <div className="mt-4 flex h-48 items-center justify-center rounded-xl bg-[var(--bg2)] muted">
              {selected.is_vaulted && !unlocked
                ? "Unlock the vault to view full image"
                : selected.status}
              {selected.error_message ? ` — ${selected.error_message}` : ""}
            </div>
          )}
          {selected.is_vaulted && !unlocked && (
            <p className="muted mt-2 text-sm">
              Showing blurred teaser only.{" "}
              <Link className="underline" to="/vault">
                Open Vault
              </Link>
            </p>
          )}
          <p className="mt-4 text-sm">{selected.expanded_prompt}</p>
          <div className="mt-4 flex flex-wrap gap-3">
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
                Open full size
              </a>
            )}
          </div>
          {!selected.is_vaulted && selected.output_path && !vaultStatus.data?.unlocked && (
            <p className="muted mt-2 text-xs">Unlock the vault (Vault page) before moving items.</p>
          )}
        </div>
      )}
    </div>
  );
}
