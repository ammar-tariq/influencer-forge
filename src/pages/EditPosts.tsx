import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { BackLink } from "../components/common/BackLink";
import { MediaImage } from "../components/common/MediaImage";
import { StatusBadge } from "../components/common/StatusBadge";

/** Replace an existing Library post with a new prompt / wardrobe (same post id). */
export function EditPosts() {
  const qc = useQueryClient();
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const [influencerId, setInfluencerId] = useState<number | "">("");
  const [selectedId, setSelectedId] = useState<number | "">("");
  const [prompt, setPrompt] = useState("");
  const [wardrobeId, setWardrobeId] = useState<number | "">("");
  const [message, setMessage] = useState<string | null>(null);

  const generations = useQuery({
    queryKey: ["generations", influencerId || "all"],
    queryFn: () =>
      api.listGenerations({
        influencer_id: influencerId === "" ? undefined : Number(influencerId),
      }),
    refetchInterval: 2000,
  });

  const wardrobe = useQuery({
    queryKey: ["wardrobe", influencerId || "all"],
    queryFn: () =>
      influencerId === ""
        ? api.listWardrobe()
        : api.listInfluencerWardrobe(Number(influencerId)),
  });

  const items = useMemo(
    () =>
      (generations.data ?? []).filter(
        (g) => g.status === "completed" && !g.is_vaulted && Boolean(g.output_path),
      ),
    [generations.data],
  );
  const selected = items.find((g) => g.id === selectedId);

  const replace = useMutation({
    mutationFn: () =>
      api.replaceGeneration(Number(selectedId), {
        user_prompt: prompt.trim(),
        wardrobe_item_id: wardrobeId === "" ? null : Number(wardrobeId),
        is_nsfw: false,
      }),
    onSuccess: (g) => {
      setMessage(`Post #${g.id} queued for replacement`);
      qc.invalidateQueries({ queryKey: ["generations"] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackLink fallbackTo="/history" label="Back" />
      </div>
      <header>
        <h1 className="text-3xl tracking-tight">Edit posts</h1>
        <p className="muted mt-1">
          Pick a post and replace it with a new scene or outfit. The same post id is kept in the
          Library.
        </p>
      </header>

      <div className="panel space-y-1">
        <div className="field">
          <label>Filter by influencer</label>
          <select
            value={influencerId}
            onChange={(e) => {
              setInfluencerId(e.target.value ? Number(e.target.value) : "");
              setSelectedId("");
            }}
          >
            <option value="">All</option>
            {(influencers.data ?? []).map((inf) => (
              <option key={inf.id} value={inf.id}>
                {inf.name}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Post to replace</label>
          <select
            value={selectedId}
            onChange={(e) => {
              const id = e.target.value ? Number(e.target.value) : "";
              setSelectedId(id);
              const g = items.find((x) => x.id === id);
              if (g) {
                setPrompt(g.user_prompt);
                setWardrobeId(g.wardrobe_item_id ?? "");
                setInfluencerId(g.influencer_id);
              }
            }}
          >
            <option value="">Select…</option>
            {items.map((g) => (
              <option key={g.id} value={g.id}>
                #{g.id} · {g.user_prompt.slice(0, 48)}
              </option>
            ))}
          </select>
        </div>

        {selected && (
          <div className="mb-4">
            <MediaImage
              path={selected.output_path}
              alt={`Post ${selected.id}`}
              className="h-56 w-full rounded-xl object-contain bg-[var(--bg2)]"
            />
            <div className="mt-2">
              <StatusBadge status={selected.status} isNsfw={selected.is_nsfw} />
            </div>
          </div>
        )}

        <div className="field">
          <label>New prompt</label>
          <textarea
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the replacement scene…"
            disabled={!selectedId}
          />
        </div>

        <div className="field">
          <label>Wardrobe outfit (optional)</label>
          <select
            value={wardrobeId}
            disabled={!selectedId}
            onChange={(e) => setWardrobeId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">None</option>
            {(wardrobe.data ?? []).map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
          <p className="muted mt-1 text-xs">
            Assigned / shared outfits for this influencer. Create more under Wardrobe.
          </p>
        </div>

        <button
          className="btn"
          disabled={!selectedId || !prompt.trim() || replace.isPending}
          onClick={() => replace.mutate()}
        >
          {replace.isPending ? "Queuing…" : "Replace post"}
        </button>
        {message && <p className="mt-3 text-sm text-[var(--accent-2)]">{message}</p>}
      </div>
    </div>
  );
}
