import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { MediaImage } from "../components/common/MediaImage";
import { ReadinessChecklist } from "../components/common/ReadinessChecklist";
import { BackLink } from "../components/common/BackLink";
import { StatusBadge } from "../components/common/StatusBadge";
import { IconSpinner } from "../components/common/icons";
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

  const wardrobe = useQuery({
    queryKey: ["wardrobe", influencerId || "none"],
    queryFn: () => api.listInfluencerWardrobe(Number(influencerId)),
    enabled: influencerId !== "",
  });

  const selected = influencers.data?.find((i) => i.id === influencerId);
  const personality = personalities.data?.find((p) => p.id === selected?.personality_id);
  const ageRating = selected?.age_rating ?? personality?.age_rating ?? null;
  const nsfwAllowed = Boolean(selected) && !nsfwBlocked(ageRating);
  const wardrobeItem = (wardrobe.data ?? []).find((w) => w.id === wardrobeId);

  const scene = useMemo(() => {
    // Wardrobe outfit always wins over dressing presets (stable; do not gate on nsfw).
    if (wardrobeItem) {
      return composeScenePrompt({
        framing,
        pose,
        dressing: "other",
        setting,
        poseOther,
        dressingOther: wardrobeItem.prompt_keywords,
        settingOther,
        notes,
      });
    }
    return composeScenePrompt({
      framing,
      pose,
      dressing,
      setting,
      poseOther,
      dressingOther,
      settingOther,
      notes,
    });
  }, [
    framing,
    pose,
    dressing,
    setting,
    poseOther,
    dressingOther,
    settingOther,
    notes,
    wardrobeItem,
  ]);

  useEffect(() => {
    setWardrobeId("");
  }, [influencerId]);

  // Keep dressing controls in sync with wardrobe so the UI doesn't show a stale preset.
  useEffect(() => {
    if (!wardrobeItem) return;
    setDressing("other");
    setDressingOther(wardrobeItem.prompt_keywords);
  }, [wardrobeItem?.id, wardrobeItem?.prompt_keywords]);

  // NSFW defaults — never derive from scene.nsfw while wardrobe can change scene
  // (that loop flipped wardrobe ↔ dressing prompts every render).
  useEffect(() => {
    if (!selected || nsfwBlocked(ageRating)) {
      setNsfw(false);
      return;
    }
    if (ageRating === "18+") {
      setNsfw(true);
    }
  }, [selected?.id, ageRating]);

  useEffect(() => {
    if (!nsfwAllowed) return;
    if (wardrobeItem) {
      if (/\b(nude|topless|naked|lingerie)\b/i.test(wardrobeItem.prompt_keywords)) {
        setNsfw(true);
      }
      return;
    }
    const dressOpt = DRESSINGS.find((d) => d.value === dressing);
    if (dressOpt?.nsfw) setNsfw(true);
  }, [nsfwAllowed, wardrobeItem?.id, wardrobeItem?.prompt_keywords, dressing]);

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
        wardrobe_item_id: wardrobeId === "" ? undefined : Number(wardrobeId),
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
  const resultIsVideo =
    result?.workflow_type === "video" ||
    Boolean(result?.output_path?.match(/\.(mp4|webm|mov)$/i));
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
      <div className="flex flex-wrap items-center gap-3">
        <BackLink
          fallbackTo={influencerId !== "" ? `/influencers/${influencerId}` : "/influencers"}
          label="Back"
        />
      </div>
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
            Explicit outfit selected — turn on <strong>Privacy vault</strong> in the sidebar and set
            a PIN so NSFW outputs encrypt automatically.
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
                </option>
              ))}
            </select>
            {influencerId !== "" && (
              <p className="muted mt-2 text-sm">
                <Link className="underline" to={`/influencers/${influencerId}`}>
                  View profile
                </Link>
              </p>
            )}
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
            <label>Wardrobe outfit (consistent clothing)</label>
            <select
              value={wardrobeId}
              disabled={influencerId === ""}
              onChange={(e) => setWardrobeId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">None — use dressing preset below</option>
              {(wardrobe.data ?? []).map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
            {influencerId !== "" && !(wardrobe.data ?? []).length && (
              <p className="muted mt-1 text-xs">
                No outfits for this influencer yet.{" "}
                <Link className="underline" to="/wardrobe">
                  Create & assign in Wardrobe
                </Link>
              </p>
            )}
            {wardrobeItem && (
              <p className="muted mt-1 text-xs">Wearing: {wardrobeItem.prompt_keywords}</p>
            )}
          </div>

          <div className="field">
            <label>Dressing {wardrobeItem ? "(from wardrobe)" : ""}</label>
            <select
              value={dressing}
              disabled={Boolean(wardrobeItem)}
              onChange={(e) => setDressing(e.target.value)}
            >
              {DRESSINGS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                  {d.nsfw ? " · NSFW" : ""}
                </option>
              ))}
            </select>
            {dressing === "other" && !wardrobeItem && (
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
              className="h-48 w-full rounded-xl object-cover media-face"
              fallback={selected ? "No portrait yet" : "Select an influencer"}
              faceFocus
            />
            {selected && <p className="mt-2 text-sm">{selected.name}</p>}
          </div>
          <div className="panel">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide muted">Progress</h2>
            {progressLabel && result ? (
              <div className="mb-3">
                <div className="progress-status">
                  <StatusBadge status={result.status} />
                  <span className="muted text-xs">#{activeId}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[var(--bg2)]">
                  <div
                    className={`h-full rounded-full transition-all ${
                      result.status === "failed" ? "bg-[var(--danger)]" : "bg-[var(--accent)]"
                    }`}
                    style={{
                      width:
                        result.status === "completed" || result.status === "failed"
                          ? "100%"
                          : result.status === "processing"
                            ? "66%"
                            : "25%",
                    }}
                  />
                </div>
              </div>
            ) : (
              <p className="muted mb-3 text-sm">Generate to see live progress here.</p>
            )}
            {result && result.status !== "completed" && result.status !== "failed" ? (
              <div className="flex h-48 flex-col items-center justify-center gap-2 rounded-xl bg-[var(--bg2)]">
                <IconSpinner size={28} className="spin text-[var(--accent-2)]" />
                <StatusBadge status={result.status} />
              </div>
            ) : (
              <MediaImage
                path={resultSrc}
                alt="Generated post"
                className="h-48 w-full rounded-xl object-cover"
                fallback={activeId ? "Waiting for output…" : "Result preview"}
                isVideo={resultIsVideo}
              />
            )}
            {result?.status === "completed" && (
              <div className="mt-3 flex flex-wrap gap-2">
                <Link
                  className="btn secondary inline-block text-sm"
                  to={
                    influencerId !== ""
                      ? `/history?influencer=${influencerId}`
                      : "/history"
                  }
                >
                  Open in Library
                </Link>
                {influencerId !== "" && (
                  <Link
                    className="btn secondary inline-block text-sm"
                    to={`/influencers/${influencerId}`}
                  >
                    Influencer profile
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
