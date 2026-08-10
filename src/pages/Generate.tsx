import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { MediaImage } from "../components/common/MediaImage";
import { ReadinessChecklist } from "../components/common/ReadinessChecklist";
import {
  ASPECT_RATIOS,
  DRESSINGS,
  FRAMINGS,
  POSES,
  SETTINGS,
  WORKFLOW_TYPES,
  composeScenePrompt,
} from "../constants/options";
import { useQueue } from "../hooks/useQueue";
import { useVault } from "../hooks/useVault";

function nsfwBlocked(ageRating?: string | null) {
  return ageRating === "Family" || ageRating === "Teen";
}

export function Generate() {
  const location = useLocation();
  const created = location.state as { createdId?: number; name?: string } | null;
  const qc = useQueryClient();
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const personalities = useQuery({ queryKey: ["personalities"], queryFn: api.listPersonalities });
  const wardrobe = useQuery({ queryKey: ["wardrobe"], queryFn: api.listWardrobe });
  const readiness = useQuery({ queryKey: ["readiness"], queryFn: api.readiness, refetchInterval: 5000 });
  const { status: vaultStatus } = useVault();
  const queue = useQueue();

  const [influencerId, setInfluencerId] = useState<number | "">(created?.createdId ?? "");
  const [framing, setFraming] = useState("full_body");
  const [pose, setPose] = useState("standing");
  const [poseOther, setPoseOther] = useState("");
  const [dressing, setDressing] = useState("casual");
  const [dressingOther, setDressingOther] = useState("");
  const [setting, setSetting] = useState("studio");
  const [settingOther, setSettingOther] = useState("");
  const [notes, setNotes] = useState("");
  const [aspect, setAspect] = useState<"9:16" | "16:9" | "1:1">("9:16");
  const [workflow, setWorkflow] = useState<"image" | "video">("image");
  const [wardrobeId, setWardrobeId] = useState<number | "">("");
  const [nsfw, setNsfw] = useState(false);
  const [requireReal, setRequireReal] = useState(false);
  const [message, setMessage] = useState<string | null>(
    created?.name ? `Created ${created.name}. Pick a scene below — full body is the default.` : null,
  );
  const [activeId, setActiveId] = useState<number | null>(null);

  const selected = influencers.data?.find((i) => i.id === influencerId);
  const personality = personalities.data?.find((p) => p.id === selected?.personality_id);
  const ageRating = selected?.age_rating ?? personality?.age_rating ?? null;
  const nsfwAllowed = Boolean(selected) && !nsfwBlocked(ageRating);

  const scene = useMemo(
    () =>
      composeScenePrompt({
        framing,
        pose,
        dressing,
        setting,
        poseOther,
        dressingOther,
        settingOther,
        notes,
      }),
    [framing, pose, dressing, setting, poseOther, dressingOther, settingOther, notes],
  );

  useEffect(() => {
    if (!selected) {
      setNsfw(false);
      return;
    }
    if (nsfwBlocked(ageRating)) {
      setNsfw(false);
      return;
    }
    // Follow dressing preset, but keep Adult/18+ free to toggle.
    setNsfw(scene.nsfw || ageRating === "18+");
  }, [selected?.id, ageRating, scene.nsfw]);

  useEffect(() => {
    if (scene.nsfw && nsfwAllowed) setNsfw(true);
  }, [scene.nsfw, nsfwAllowed]);

  const active = useQuery({
    queryKey: ["generation", activeId],
    queryFn: () => api.getGeneration(activeId!),
    enabled: activeId != null,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 1200;
    },
  });

  const mutate = useMutation({
    mutationFn: () =>
      api.createGeneration({
        influencer_id: Number(influencerId),
        user_prompt: scene.prompt,
        aspect_ratio: aspect,
        workflow_type: workflow,
        wardrobe_item_id: nsfw || wardrobeId === "" ? undefined : Number(wardrobeId),
        is_nsfw: nsfw || scene.nsfw,
        require_real: requireReal,
      }),
    onSuccess: (gen) => {
      setActiveId(gen.id);
      setMessage(`Queued #${gen.id}${gen.is_nsfw ? " (NSFW)" : ""} — watch progress on the right`);
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
      ? (result.output_path ?? result.output_thumbnail_path ?? result.teaser_path)
      : null;
  const progressLabel =
    result?.status === "pending" || result?.status === "queued"
      ? "Queued…"
      : result?.status === "processing"
        ? "Generating with ComfyUI…"
        : result?.status === "completed"
          ? "Done"
          : result?.status === "failed"
            ? "Failed"
            : null;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Create a post</h1>
        <p className="muted mt-1">
          Pick framing, pose, and outfit — you don’t have to invent prompts. Queue{" "}
          {queue.data?.pending ?? 0} pending · {queue.data?.processing ?? 0} processing ·{" "}
          <span className={mode === "real" ? "text-[var(--accent)]" : "text-[var(--accent-2)]"}>
            {mode} mode
          </span>
        </p>
      </header>

      {!influencers.data?.length && (
        <div className="panel border-[var(--accent-2)]">
          <p className="text-sm">
            No influencers yet.{" "}
            <Link className="underline" to="/wizard">
              Create one first
            </Link>
            .
          </p>
        </div>
      )}

      {mode === "stub" && <ReadinessChecklist />}

      {nsfw && !vaultStatus.data?.configured && (
        <div className="panel border-[var(--accent-2)]">
          <p className="text-sm">
            Explicit outfit selected — set a{" "}
            <Link className="underline" to="/vault">
              Vault PIN
            </Link>{" "}
            so NSFW outputs can be encrypted.
          </p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.2fr_280px]">
        <div className="panel space-y-1">
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
                  {inf.face_lock && inf.face_lock !== "none" ? " · face locked" : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label>Framing (what’s in the photo)</label>
            <select value={framing} onChange={(e) => setFraming(e.target.value)}>
              {FRAMINGS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label>Pose</label>
            <select value={pose} onChange={(e) => setPose(e.target.value)}>
              {POSES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
            {pose === "other" && (
              <input
                className="mt-2"
                value={poseOther}
                onChange={(e) => setPoseOther(e.target.value)}
                placeholder="Describe the pose…"
              />
            )}
          </div>

          <div className="field">
            <label>Dressing</label>
            <select value={dressing} onChange={(e) => setDressing(e.target.value)}>
              {DRESSINGS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                  {d.nsfw ? " · NSFW" : ""}
                </option>
              ))}
            </select>
            {dressing === "other" && (
              <input
                className="mt-2"
                value={dressingOther}
                onChange={(e) => setDressingOther(e.target.value)}
                placeholder="Describe clothing or nude state…"
              />
            )}
          </div>

          <div className="field">
            <label>Setting</label>
            <select value={setting} onChange={(e) => setSetting(e.target.value)}>
              {SETTINGS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            {setting === "other" && (
              <input
                className="mt-2"
                value={settingOther}
                onChange={(e) => setSettingOther(e.target.value)}
                placeholder="Describe the location…"
              />
            )}
          </div>

          <div className="field">
            <label>Extra notes (optional)</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. soft smile, wind in hair…"
            />
          </div>

          <div className="field">
            <label>Prompt preview</label>
            <p className="rounded-xl bg-[var(--bg2)] p-3 text-sm">{scene.prompt || "—"}</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
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
          </div>

          <div className="field">
            <label>Wardrobe item (optional, SFW only)</label>
            <select
              value={wardrobeId}
              disabled={nsfw || scene.nsfw}
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

          <label className="mb-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={nsfw || scene.nsfw}
              disabled={!nsfwAllowed}
              onChange={(e) => setNsfw(e.target.checked)}
            />
            NSFW / explicit mode
            {selected && ageRating && <span className="muted">· rating {ageRating}</span>}
          </label>
          <label className="mb-4 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={requireReal}
              onChange={(e) => setRequireReal(e.target.checked)}
            />
            Require real ComfyUI output
          </label>

          {message && <p className="mb-3 text-sm text-[var(--accent)]">{message}</p>}
          {result?.status === "failed" && (
            <p className="mb-3 text-sm text-[var(--danger)]">{result.error_message ?? "Generation failed"}</p>
          )}
          <button
            className="btn"
            disabled={!influencerId || !scene.prompt || mutate.isPending}
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
            {selected && (
              <>
                <p className="mt-2 text-sm">{selected.name}</p>
                <p className="muted mt-1 text-xs">
                  Face lock:{" "}
                  {selected.face_lock === "face_seed"
                    ? "Face Seed"
                    : selected.face_lock === "base_portrait"
                      ? "Base portrait"
                      : "None yet"}
                </p>
              </>
            )}
          </div>
          <div className="panel">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide muted">Progress</h2>
            {progressLabel ? (
              <div className="mb-3">
                <div className="mb-2 flex justify-between text-xs muted">
                  <span>{progressLabel}</span>
                  <span>#{activeId}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[var(--bg2)]">
                  <div
                    className="h-full rounded-full bg-[var(--accent)] transition-all"
                    style={{
                      width:
                        result?.status === "completed"
                          ? "100%"
                          : result?.status === "processing"
                            ? "66%"
                            : result?.status === "failed"
                              ? "100%"
                              : "25%",
                    }}
                  />
                </div>
              </div>
            ) : (
              <p className="muted mb-3 text-sm">Generate to see live progress here.</p>
            )}
            {result && result.status !== "completed" && result.status !== "failed" ? (
              <div className="flex h-48 items-center justify-center rounded-xl bg-[var(--bg2)] text-sm muted">
                {result.status}…
              </div>
            ) : (
              <MediaImage
                path={resultSrc}
                alt="Generated post"
                className="h-48 w-full rounded-xl object-cover"
                fallback={activeId ? "Waiting for output…" : "Result preview"}
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
