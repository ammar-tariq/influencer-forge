import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, mediaUrl } from "../api/client";
import { MediaImage } from "../components/common/MediaImage";
import type { Generation } from "../types";

export function History() {
  const qc = useQueryClient();
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["generations"] }),
  });

  const items = useMemo(() => generations.data ?? [], [generations.data]);
  const detailSrc = selected
    ? mediaUrl(selected.output_path) ?? mediaUrl(selected.output_thumbnail_path)
    : undefined;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">History</h1>
        <p className="muted mt-1">Browse generations, inspect seeds, regenerate.</p>
      </header>

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
              path={g.output_thumbnail_path ?? g.output_path}
              alt=""
              className="mb-3 h-40 w-full rounded-xl object-cover"
              fallback={g.status}
            />
            <div className="font-semibold">
              #{g.id} · {g.status}
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
              </p>
            </div>
            <button className="btn secondary" onClick={() => setSelected(null)}>
              Close
            </button>
          </div>
          {detailSrc ? (
            <a href={detailSrc} target="_blank" rel="noreferrer">
              <img
                src={detailSrc}
                alt={`Generation ${selected.id}`}
                className="mt-4 max-h-[70vh] w-full rounded-xl object-contain bg-[var(--bg2)]"
              />
            </a>
          ) : (
            <div className="mt-4 flex h-48 items-center justify-center rounded-xl bg-[var(--bg2)] muted">
              {selected.status}
              {selected.error_message ? ` — ${selected.error_message}` : ""}
            </div>
          )}
          <p className="mt-4 text-sm">{selected.expanded_prompt}</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button className="btn" onClick={() => regenerate.mutate(selected.id)}>
              Regenerate
            </button>
            <button className="btn secondary" onClick={() => vault.mutate(selected.id)}>
              Move to vault
            </button>
            {detailSrc && (
              <a className="btn secondary" href={detailSrc} target="_blank" rel="noreferrer">
                Open full size
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
