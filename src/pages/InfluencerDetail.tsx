import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, mediaUrl, vaultRevealUrl } from "../api/client";
import { InfluencerEditPanels } from "../components/InfluencerEditPanels";
import { GenerationCard } from "../components/common/GenerationCard";
import { StatusBadge } from "../components/common/StatusBadge";
import { ImageLightbox } from "../components/common/ImageLightbox";
import { MediaImage } from "../components/common/MediaImage";
import { BackLink } from "../components/common/BackLink";
import { PinPrompt } from "../components/common/PinPrompt";
import { IconCheck } from "../components/common/icons";
import { useVaultReveal } from "../hooks/useVaultReveal";
import type { Generation } from "../types";

const DEFAULT_IDENTITY_PROMPT =
  "full body shot, head to toe visible in frame, standing naturally, wearing casual everyday outfit, clean photo studio background, face clearly visible";

function isInFlight(g: Generation) {
  return ["pending", "queued", "processing"].includes(g.status);
}

export function InfluencerDetail() {
  const { id } = useParams();
  const influencerId = Number(id);
  const navigate = useNavigate();
  const location = useLocation();
  const justCreated = Boolean((location.state as { justCreated?: boolean } | null)?.justCreated);
  const qc = useQueryClient();
  const reveal = useVaultReveal();
  const [selected, setSelected] = useState<Generation | null>(null);
  const [identityPrompt, setIdentityPrompt] = useState(DEFAULT_IDENTITY_PROMPT);
  const [faceFile, setFaceFile] = useState<File | null>(null);
  const [assignOutfit, setAssignOutfit] = useState<number | "">("");
  const [deleteArmed, setDeleteArmed] = useState(false);

  const detail = useQuery({
    queryKey: ["influencer", influencerId],
    queryFn: () => api.getInfluencer(influencerId),
    enabled: Number.isFinite(influencerId) && influencerId > 0,
    refetchInterval: 3000,
  });

  const generations = useQuery({
    queryKey: ["generations", influencerId],
    queryFn: () => api.listGenerations({ influencer_id: influencerId }),
    enabled: Number.isFinite(influencerId) && influencerId > 0,
    refetchInterval: 2000,
  });
  const vaultStatus = useQuery({ queryKey: ["vault-status"], queryFn: api.vaultStatus });

  const wardrobeAll = useQuery({ queryKey: ["wardrobe"], queryFn: api.listWardrobe });
  const wardrobeMine = useQuery({
    queryKey: ["wardrobe", influencerId],
    queryFn: () => api.listInfluencerWardrobe(influencerId),
    enabled: Number.isFinite(influencerId) && influencerId > 0,
  });

  const browseUnlocked = Boolean(vaultStatus.data?.unlocked);
  const items = useMemo(() => {
    const all = generations.data ?? [];
    if (browseUnlocked) return all;
    return all.filter((g) => !g.is_vaulted);
  }, [generations.data, browseUnlocked]);
  const inFlight = useMemo(() => items.filter(isInFlight), [items]);
  const sfwCompleted = useMemo(
    () =>
      items.filter(
        (g) =>
          g.status === "completed" &&
          !g.is_nsfw &&
          !g.is_vaulted &&
          (g.output_path || g.output_thumbnail_path),
      ),
    [items],
  );
  const selectedIndex = selected ? items.findIndex((g) => g.id === selected.id) : -1;
  const hasPrev = selectedIndex > 0;
  const hasNext = selectedIndex >= 0 && selectedIndex < items.length - 1;
  const faceLocked = Boolean(detail.data?.face_lock && detail.data.face_lock !== "none");
  const showSetup = justCreated || !faceLocked;

  useEffect(() => {
    const latest = items[0];
    if (!latest?.user_prompt?.trim()) return;
    setIdentityPrompt((prev) => (prev === DEFAULT_IDENTITY_PROMPT ? latest.user_prompt : prev));
  }, [items]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["influencer", influencerId] });
    qc.invalidateQueries({ queryKey: ["generations", influencerId] });
    qc.invalidateQueries({ queryKey: ["influencers"] });
    qc.invalidateQueries({ queryKey: ["wardrobe", influencerId] });
  };

  const remove = useMutation({
    mutationFn: () => api.deleteInfluencer(influencerId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["influencers"] });
      navigate("/influencers");
    },
  });

  const tryIdentity = useMutation({
    mutationFn: () =>
      api.createGenerationBatch({
        influencer_id: influencerId,
        user_prompt: identityPrompt.trim() || DEFAULT_IDENTITY_PROMPT,
        aspect_ratio: "9:16",
        workflow_type: "image",
        is_nsfw: false,
        count: 4,
        identity_explore: true,
      }),
    onSuccess: invalidate,
  });

  const regenerate = useMutation({
    mutationFn: ({ gid, explore }: { gid: number; explore?: boolean }) =>
      api.regenerate(gid, explore != null ? { identity_explore: explore } : undefined),
    onSuccess: invalidate,
  });

  const lockFace = useMutation({
    mutationFn: (generationId: number) =>
      api.lockFace(influencerId, { generation_id: generationId }),
    onSuccess: () => {
      invalidate();
      setSelected(null);
    },
  });

  const uploadSeed = useMutation({
    mutationFn: async () => {
      if (!faceFile || !detail.data?.looks_id) throw new Error("Choose a face image first");
      await api.uploadFaceSeed(detail.data.looks_id, faceFile);
    },
    onSuccess: () => {
      setFaceFile(null);
      invalidate();
    },
  });

  const assignWardrobe = useMutation({
    mutationFn: () => api.assignWardrobe(influencerId, Number(assignOutfit)),
    onSuccess: () => {
      setAssignOutfit("");
      invalidate();
      qc.invalidateQueries({ queryKey: ["wardrobe"] });
    },
  });

  const unassignWardrobe = useMutation({
    mutationFn: (itemId: number) => api.unassignWardrobe(influencerId, itemId),
    onSuccess: invalidate,
  });

  if (!Number.isFinite(influencerId) || influencerId <= 0) {
    return (
      <div className="panel">
        <p className="text-[var(--danger)]">Invalid influencer link.</p>
        <BackLink fallbackTo="/influencers" label="Influencers" />
      </div>
    );
  }

  if (detail.isLoading) {
    return <p className="muted">Loading influencer…</p>;
  }
  if (detail.isError || !detail.data) {
    return (
      <div className="panel space-y-3">
        <p className="text-[var(--danger)]">Influencer not found.</p>
        <BackLink fallbackTo="/influencers" label="Influencers" />
      </div>
    );
  }

  const inf = detail.data;
  const looks = inf.looks;
  const mine = wardrobeMine.data ?? [];
  const mineIds = new Set(mine.map((w) => w.id));
  const assignable = (wardrobeAll.data ?? []).filter((w) => !mineIds.has(w.id) || w.is_shared);

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

  const heroPath =
    looks?.base_portrait_path ||
    looks?.reference_image_path ||
    inf.avatar_path ||
    sfwCompleted[0]?.output_thumbnail_path ||
    sfwCompleted[0]?.output_path;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackLink fallbackTo="/influencers" label="Back" />
      </div>

      <header className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <MediaImage
          path={heroPath}
          alt={inf.name}
          className="h-72 w-full rounded-2xl object-cover media-face"
          fallback={inFlight.length ? "Generating…" : "No photo yet"}
        />
        <div>
          <h1 className="text-3xl tracking-tight">{inf.name}</h1>
          <p className="muted mt-2 text-sm">
            {inf.niche ?? "Creator"}
            {inf.age_rating ? ` · ${inf.age_rating}` : ""}
            {` · ${inf.generation_count ?? items.length} posts`}
          </p>
          {inf.personality?.bio && <p className="mt-3 text-sm">{inf.personality.bio}</p>}
          <div className="mt-5 flex flex-wrap gap-2">
            <Link className="btn" to="/generate" state={{ createdId: inf.id, name: inf.name }}>
              Create post
            </Link>
            <Link className="btn secondary" to="/edit-posts">
              Edit posts
            </Link>
            {!deleteArmed ? (
              <button
                className="btn secondary"
                disabled={remove.isPending}
                onClick={() => setDeleteArmed(true)}
              >
                Delete
              </button>
            ) : (
              <>
                <button
                  className="btn"
                  style={{ background: "var(--danger)", color: "#1a0a0a" }}
                  disabled={remove.isPending}
                  onClick={() => remove.mutate()}
                >
                  {remove.isPending ? "Deleting…" : `Yes, delete ${inf.name}`}
                </button>
                <button
                  className="btn secondary"
                  disabled={remove.isPending}
                  onClick={() => setDeleteArmed(false)}
                >
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {showSetup && (
        <section className="panel border-[var(--accent)]">
          <h2 className="text-xl tracking-tight">
            {justCreated ? "Pick their face" : "Identity shots"}
          </h2>
          <p className="muted mt-2 text-sm">
            Queue four face options (they fill in as the queue finishes), then lock the one you want
            later posts to keep — or upload a Face Seed instead.
          </p>

          {inFlight.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl bg-[var(--bg2)] px-4 py-3 text-sm">
              <StatusBadge status={inFlight[0]?.status ?? "processing"} />
              <span className="muted">
                {inFlight.length === 1
                  ? `Shot #${inFlight[0]?.id} in progress`
                  : `${inFlight.length} face options queued / generating`}
              </span>
            </div>
          )}

          <div className="field mt-4">
            <label>Identity prompt</label>
            <textarea
              rows={3}
              value={identityPrompt}
              onChange={(e) => setIdentityPrompt(e.target.value)}
              placeholder={DEFAULT_IDENTITY_PROMPT}
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              className="btn"
              disabled={tryIdentity.isPending || !identityPrompt.trim()}
              onClick={() => tryIdentity.mutate()}
            >
              {tryIdentity.isPending ? "Queuing…" : "Generate 4 face options"}
            </button>
          </div>

          <div className="field mt-6">
            <label>Or upload a Face Seed</label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setFaceFile(e.target.files?.[0] ?? null)}
            />
            <button
              className="btn secondary mt-2"
              disabled={!faceFile || uploadSeed.isPending}
              onClick={() => uploadSeed.mutate()}
            >
              {uploadSeed.isPending ? "Uploading…" : "Upload & use as face"}
            </button>
          </div>

          {sfwCompleted.length > 0 && (
            <div className="mt-6 space-y-3">
              <h3 className="text-lg">Choose a shot</h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {sfwCompleted.slice(0, 9).map((g) => (
                  <div key={g.id} className="rounded-xl bg-[var(--bg2)] p-3">
                    <button type="button" className="gen-card-media w-full" onClick={() => setSelected(g)}>
                      <MediaImage
                        path={cardPath(g)}
                        alt=""
                        className="mb-2 h-44 w-full rounded-lg object-cover media-face"
                        fallback="No preview"
                      />
                    </button>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="btn" disabled={lockFace.isPending} onClick={() => lockFace.mutate(g.id)}>
                        <span className="inline-flex items-center gap-1">
                          <IconCheck size={14} /> Use this face
                        </span>
                      </button>
                      <button
                        className="btn secondary"
                        disabled={regenerate.isPending}
                        onClick={() => regenerate.mutate({ gid: g.id, explore: true })}
                      >
                        Re-roll
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      <InfluencerEditPanels
        detail={inf}
        onSaved={() => {
          invalidate();
        }}
      />

      <section className="panel space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl tracking-tight">Wardrobe</h2>
            <p className="muted text-sm">
              Outfits assigned here show up when creating posts for {inf.name}.
            </p>
          </div>
          <Link className="btn secondary" to="/wardrobe">
            Manage wardrobe
          </Link>
        </div>
        {!mine.length ? (
          <p className="muted text-sm">No outfits assigned yet.</p>
        ) : (
          <ul className="space-y-2">
            {mine.map((w) => (
              <li
                key={w.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-[var(--bg2)] px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium">{w.name}</span>
                  <span className="muted"> · {w.category}</span>
                  <p className="muted text-xs">{w.prompt_keywords}</p>
                </div>
                {!w.is_shared && (
                  <button
                    type="button"
                    className="btn secondary"
                    onClick={() => unassignWardrobe.mutate(w.id)}
                  >
                    Remove
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap gap-2">
          <select
            value={assignOutfit}
            onChange={(e) => setAssignOutfit(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Add outfit…</option>
            {assignable.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
          <button
            className="btn secondary"
            disabled={!assignOutfit || assignWardrobe.isPending}
            onClick={() => assignWardrobe.mutate()}
          >
            Assign
          </button>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-2xl tracking-tight">Posts</h2>
          <p className="muted text-sm">Everything this influencer has produced.</p>
        </div>

        {!items.length ? (
          <div className="panel">
            <p className="muted text-sm">No posts yet.</p>
            <Link className="btn mt-3 inline-block" to="/generate" state={{ createdId: inf.id }}>
              Create post
            </Link>
          </div>
        ) : (
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
        )}
      </section>

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
        title={selected ? `Post #${selected.id}` : ""}
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
              ? `${detailSrc}?t=${selected.id}-v`
              : detailSrc
            : null
        }
        placeholder={selected?.status ?? "No image"}
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
              {!selected.is_nsfw && !selected.is_vaulted && selected.status === "completed" && (
                <button
                  className="btn"
                  disabled={lockFace.isPending}
                  onClick={() => lockFace.mutate(selected.id)}
                >
                  Use this face
                </button>
              )}
              <button
                className="btn secondary"
                onClick={() => regenerate.mutate({ gid: selected.id, explore: false })}
              >
                Regenerate
              </button>
              <Link className="btn secondary" to="/edit-posts">
                Replace post
              </Link>
            </div>
          </>
        )}
      </ImageLightbox>
    </div>
  );
}
