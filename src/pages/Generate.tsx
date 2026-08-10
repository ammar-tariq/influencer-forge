import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { MediaImage } from "../components/common/MediaImage";
import { ReadinessChecklist } from "../components/common/ReadinessChecklist";
import { ASPECT_RATIOS, WORKFLOW_TYPES } from "../constants/options";
import { useQueue } from "../hooks/useQueue";

export function Generate() {
  const qc = useQueryClient();
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const wardrobe = useQuery({ queryKey: ["wardrobe"], queryFn: api.listWardrobe });
  const readiness = useQuery({ queryKey: ["readiness"], queryFn: api.readiness, refetchInterval: 5000 });
  const queue = useQueue();
  const [influencerId, setInfluencerId] = useState<number | "">("");
  const [prompt, setPrompt] = useState("golden hour portrait outdoors");
  const [aspect, setAspect] = useState<"9:16" | "16:9" | "1:1">("9:16");
  const [workflow, setWorkflow] = useState<"image" | "video">("image");
  const [wardrobeId, setWardrobeId] = useState<number | "">("");
  const [requireReal, setRequireReal] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<number | null>(null);

  const selected = influencers.data?.find((i) => i.id === influencerId);

  const active = useQuery({
    queryKey: ["generation", activeId],
    queryFn: () => api.getGeneration(activeId!),
    enabled: activeId != null,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 1500;
    },
  });

  const mutate = useMutation({
    mutationFn: () =>
      api.createGeneration({
        influencer_id: Number(influencerId),
        user_prompt: prompt,
        aspect_ratio: aspect,
        workflow_type: workflow,
        wardrobe_item_id: wardrobeId === "" ? undefined : Number(wardrobeId),
        require_real: requireReal,
      }),
    onSuccess: (gen) => {
      setActiveId(gen.id);
      setMessage(`Queued generation #${gen.id}`);
      qc.invalidateQueries({ queryKey: ["generations"] });
      qc.invalidateQueries({ queryKey: ["queue"] });
      qc.invalidateQueries({ queryKey: ["influencers"] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const mode = readiness.data?.mode ?? "stub";
  const result = active.data;
  const resultSrc =
    result?.status === "completed"
      ? (result.output_path ?? result.output_thumbnail_path)
      : null;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Generate</h1>
        <p className="muted mt-1">
          Queue {queue.data?.pending ?? 0} pending · {queue.data?.processing ?? 0} processing ·{" "}
          <span className={mode === "real" ? "text-[var(--accent)]" : "text-[var(--accent-2)]"}>
            {mode} mode
          </span>
        </p>
      </header>

      {mode === "stub" && <ReadinessChecklist />}

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="panel">
          <div className="field">
            <label>Influencer</label>
            <select
              value={influencerId}
              onChange={(e) => setInfluencerId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Select…</option>
              {(influencers.data ?? []).map((inf) => (
                <option key={inf.id} value={inf.id}>
                  {inf.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Prompt</label>
            <textarea rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </div>
          <div className="field">
            <label>Type</label>
            <select value={workflow} onChange={(e) => setWorkflow(e.target.value as "image" | "video")}>
              {WORKFLOW_TYPES.map((w) => (
                <option key={w.value} value={w.value}>
                  {w.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Aspect ratio</label>
            <select value={aspect} onChange={(e) => setAspect(e.target.value as typeof aspect)}>
              {ASPECT_RATIOS.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Wardrobe (optional)</label>
            <select
              value={wardrobeId}
              onChange={(e) => setWardrobeId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">None</option>
              {(wardrobe.data ?? []).map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>
          <label className="mb-4 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={requireReal}
              onChange={(e) => setRequireReal(e.target.checked)}
            />
            Require real ComfyUI output (fail instead of placeholder)
          </label>
          {message && <p className="mb-3 text-sm text-[var(--accent)]">{message}</p>}
          {result?.status === "failed" && (
            <p className="mb-3 text-sm text-[var(--danger)]">{result.error_message ?? "Generation failed"}</p>
          )}
          <button
            className="btn"
            disabled={!influencerId || !prompt || mutate.isPending}
            onClick={() => mutate.mutate()}
          >
            {mutate.isPending ? "Queueing…" : "Generate"}
          </button>
        </div>

        <div className="space-y-4">
          <div className="panel">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide muted">Model</h2>
            <MediaImage
              path={selected?.avatar_path}
              alt={selected?.name ?? "Model"}
              className="h-48 w-full rounded-xl object-cover"
              fallback={selected ? "No portrait yet" : "Select an influencer"}
            />
            {selected && <p className="mt-2 text-sm">{selected.name}</p>}
          </div>
          <div className="panel">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide muted">Result</h2>
            {result && result.status !== "completed" && result.status !== "failed" ? (
              <div className="flex h-48 items-center justify-center rounded-xl bg-[var(--bg2)] text-sm muted">
                {result.status}…
              </div>
            ) : (
              <MediaImage
                path={resultSrc}
                alt="Generated post"
                className="h-48 w-full rounded-xl object-cover"
                fallback={activeId ? "Waiting for output…" : "Generate to preview"}
              />
            )}
            {result?.status === "completed" && (
              <Link className="btn secondary mt-3 inline-block text-sm" to="/history">
                Open in History
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
