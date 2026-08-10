import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useQueue } from "../hooks/useQueue";
import { ReadinessChecklist } from "../components/common/ReadinessChecklist";

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
      setMessage(
        `Queued generation #${gen.id} (${requireReal ? "real-only" : "stub allowed if needed"})`,
      );
      qc.invalidateQueries({ queryKey: ["generations"] });
      qc.invalidateQueries({ queryKey: ["queue"] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const mode = readiness.data?.mode ?? "stub";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
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
            <option value="image">Image</option>
            <option value="video">Video (AnimateDiff path)</option>
          </select>
        </div>
        <div className="field">
          <label>Aspect ratio</label>
          <select value={aspect} onChange={(e) => setAspect(e.target.value as typeof aspect)}>
            <option value="9:16">9:16</option>
            <option value="16:9">16:9</option>
            <option value="1:1">1:1</option>
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
        <button
          className="btn"
          disabled={!influencerId || !prompt || mutate.isPending}
          onClick={() => mutate.mutate()}
        >
          {mutate.isPending ? "Queueing…" : "Generate"}
        </button>
      </div>
    </div>
  );
}
