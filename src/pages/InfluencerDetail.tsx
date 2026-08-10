import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, mediaUrl, vaultRevealUrl } from "../api/client";
import { ImageLightbox } from "../components/common/ImageLightbox";
import { MediaImage } from "../components/common/MediaImage";
import type { Generation } from "../types";

const DEFAULT_IDENTITY_PROMPT =
  "full body shot, head to toe visible in frame, standing naturally, wearing casual everyday outfit, clean photo studio background, face clearly visible";

function bodyEntries(body?: Record<string, string> | null) {
  if (!body) return [];
  return Object.entries(body).filter(([, v]) => Boolean(v));
}

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
  const [selected, setSelected] = useState<Generation | null>(null);
  const [identityPrompt, setIdentityPrompt] = useState(DEFAULT_IDENTITY_PROMPT);
  const [faceFile, setFaceFile] = useState<File | null>(null);

  const detail = useQuery({
    queryKey: ["influencer", influencerId],
    queryFn: () => api.getInfluencer(influencerId),
    enabled: Number.isFinite(influencerId) && influencerId > 0,
    refetchInterval: 3000,
  });

  const vaultStatus = useQuery({ queryKey: ["vault-status"], queryFn: api.vaultStatus });

  const generations = useQuery({
    queryKey: ["generations", influencerId],
    queryFn: () => api.listGenerations({ influencer_id: influencerId }),
    enabled: Number.isFinite(influencerId) && influencerId > 0,
    refetchInterval: 2000,
  });

  const items = generations.data ?? [];
  const inFlight = useMemo(() => items.filter(isInFlight), [items]);
  const sfwCompleted = useMemo(
    () =>
      items.filter(
        (g) => g.status === "completed" && !g.is_nsfw && !g.is_vaulted && (g.output_path || g.output_thumbnail_path),
      ),
    [items],
  );

  useEffect(() => {
    const latest = items[0];
    if (!latest?.user_prompt?.trim()) return;
    setIdentityPrompt((prev) => (prev === DEFAULT_IDENTITY_PROMPT ? latest.user_prompt : prev));
  }, [items]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["influencer", influencerId] });
    qc.invalidateQueries({ queryKey: ["generations", influencerId] });
    qc.invalidateQueries({ queryKey: ["influencers"] });
  };

  const archive = useMutation({
    mutationFn: () => api.archiveInfluencer(influencerId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["influencers"] });
      navigate("/influencers");
    },
  });

  const tryIdentity = useMutation({
    mutationFn: () =>
      api.createGeneration({
        influencer_id: influencerId,
        user_prompt: identityPrompt.trim() || DEFAULT_IDENTITY_PROMPT,
        aspect_ratio: "9:16",
        workflow_type: "image",
        is_nsfw: false,
      }),
    onSuccess: invalidate,
  });

  const regenerate = useMutation({
    mutationFn: (gid: number) => api.regenerate(gid),
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

  const clearLock = useMutation({
    mutationFn: () => api.lockFace(influencerId, { clear: true }),
    onSuccess: invalidate,
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

  if (!Number.isFinite(influencerId) || influencerId <= 0) {
    return (
      <div className="panel">
        <p className="text-[var(--danger)]">Invalid influencer link.</p>
        <Link className="btn mt-4 inline-block" to="/influencers">
          Back to Influencers
        </Link>
      </div>
    );
  }

  if (detail.isLoading) {
    return <p className="muted">Loading influencer…</p>;
  }
  if (detail.isError || !detail.data) {
    return (
      <div className="panel">
        <p className="text-[var(--danger)]">Influencer not found.</p>
        <p className="muted mt-2 text-sm">
          If you just created them, restart the app so the API picks up the latest routes, then open{" "}
          <Link className="underline" to="/influencers">
            Influencers
          </Link>
          .
        </p>
        <Link className="btn mt-4 inline-block" to="/influencers">
          Back to Influencers
        </Link>
      </div>
    );
  }

  const inf = detail.data;
  const looks = inf.looks;
  const personality = inf.personality;
  const unlocked = Boolean(vaultStatus.data?.unlocked);
  const faceLocked = Boolean(inf.face_lock && inf.face_lock !== "none");
  const showSetup = justCreated || !faceLocked;

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

  const heroPath =
    looks?.base_portrait_path ||
    looks?.reference_image_path ||
    inf.avatar_path ||
    sfwCompleted[0]?.output_thumbnail_path ||
    sfwCompleted[0]?.output_path;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <Link className="muted hover:text-[var(--ink)]" to="/influencers">
          ← All influencers
        </Link>
      </div>

      <header className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <MediaImage
          path={heroPath}
          alt={inf.name}
          className="h-72 w-full rounded-2xl object-cover"
          fallback={inFlight.length ? "Generating…" : "No photo yet"}
        />
        <div>
          <h1 className="text-3xl tracking-tight">{inf.name}</h1>
          <p className="muted mt-2">
            {inf.niche ?? "Creator"}
            {inf.age_rating ? ` · ${inf.age_rating}` : ""}
            {faceLocked
              ? ` · face lock: ${String(inf.face_lock).replace("_", " ")}`
              : " · face not locked yet"}
            {` · ${inf.generation_count ?? items.length} posts`}
          </p>
          {personality?.bio && <p className="mt-3 text-sm">{personality.bio}</p>}
          <div className="mt-5 flex flex-wrap gap-2">
            <Link className="btn" to="/generate" state={{ createdId: inf.id, name: inf.name }}>
              Create post
            </Link>
            <Link className="btn secondary" to={`/history?influencer=${inf.id}`}>
              All posts in Library
            </Link>
            {faceLocked && (
              <button
                className="btn secondary"
                disabled={clearLock.isPending}
                onClick={() => {
                  if (confirm("Clear face lock so you can pick a new identity shot?")) {
                    clearLock.mutate();
                  }
                }}
              >
                Unlock face
              </button>
            )}
            <button
              className="btn secondary"
              disabled={archive.isPending}
              onClick={() => {
                if (confirm(`Archive ${inf.name}? They’ll hide from the list.`)) {
                  archive.mutate();
                }
              }}
            >
              Archive
            </button>
          </div>
        </div>
      </header>

      {showSetup && (
        <section className="panel border-[var(--accent)]">
          <h2 className="text-xl tracking-tight">
            {justCreated ? "Almost there — lock their face" : "Face lock setup"}
          </h2>
          <p className="muted mt-2 text-sm">
            Review the identity shots below. Tweak the prompt and try again until you like the face,
            then lock it. Later posts will keep that look (img2img).
          </p>

          {inFlight.length > 0 && (
            <div className="mt-4 rounded-xl bg-[var(--bg2)] px-4 py-3 text-sm">
              <div className="font-semibold">Generating identity shot…</div>
              <p className="muted mt-1">
                {inFlight.length} job{inFlight.length === 1 ? "" : "s"} in progress
                {inFlight[0] ? ` (#${inFlight[0].id} · ${inFlight[0].status})` : ""}. This page
                refreshes automatically.
              </p>
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
              {tryIdentity.isPending ? "Queuing…" : inFlight.length ? "Queue another try" : "Generate identity shot"}
            </button>
          </div>
          {tryIdentity.isError && (
            <p className="mt-2 text-sm text-[var(--danger)]">{(tryIdentity.error as Error).message}</p>
          )}

          <div className="field mt-6">
            <label>Or upload a Face Seed (instant lock)</label>
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
              {uploadSeed.isPending ? "Uploading…" : "Upload & lock face"}
            </button>
            {uploadSeed.isError && (
              <p className="mt-2 text-sm text-[var(--danger)]">{(uploadSeed.error as Error).message}</p>
            )}
          </div>

          {sfwCompleted.length > 0 && (
            <div className="mt-6 space-y-3">
              <h3 className="text-lg">Pick a shot to lock</h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {sfwCompleted.slice(0, 9).map((g) => (
                  <div key={g.id} className="rounded-xl bg-[var(--bg2)] p-3">
                    <MediaImage
                      path={cardPath(g)}
                      alt=""
                      className="mb-2 h-44 w-full rounded-lg object-cover"
                      fallback={g.status}
                    />
                    <p className="muted line-clamp-2 text-xs">{g.user_prompt}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="btn" disabled={lockFace.isPending} onClick={() => lockFace.mutate(g.id)}>
                        Lock this face
                      </button>
                      <button className="btn secondary" onClick={() => setSelected(g)}>
                        View
                      </button>
                      <button
                        className="btn secondary"
                        disabled={regenerate.isPending}
                        onClick={() => regenerate.mutate(g.id)}
                      >
                        Re-roll
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              {lockFace.isError && (
                <p className="text-sm text-[var(--danger)]">{(lockFace.error as Error).message}</p>
              )}
            </div>
          )}

          {!sfwCompleted.length && !inFlight.length && (
            <p className="muted mt-4 text-sm">No identity shots yet — generate one or upload a Face Seed.</p>
          )}
        </section>
      )}

      {faceLocked && (
        <div className="panel">
          <h2 className="text-lg">Face locked</h2>
          <p className="muted mt-1 text-sm">
            New posts use this reference for consistency. Unlock above if you want to choose again.
          </p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="panel">
          <h2 className="text-lg">Personality</h2>
          {personality ? (
            <dl className="muted mt-3 space-y-2 text-sm">
              <div>
                <dt className="font-semibold text-[var(--ink)]">Niche</dt>
                <dd>{personality.niche}</dd>
              </div>
              <div>
                <dt className="font-semibold text-[var(--ink)]">Age rating</dt>
                <dd>{personality.age_rating}</dd>
              </div>
              {Object.entries(personality.traits || {}).map(([k, v]) => (
                <div key={k}>
                  <dt className="font-semibold capitalize text-[var(--ink)]">{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="muted mt-2 text-sm">No personality data.</p>
          )}
        </div>
        <div className="panel">
          <h2 className="text-lg">Looks & body</h2>
          {looks ? (
            <dl className="muted mt-3 space-y-2 text-sm">
              <div>
                <dt className="font-semibold text-[var(--ink)]">Gender</dt>
                <dd>{looks.gender ?? "—"}</dd>
              </div>
              <div>
                <dt className="font-semibold text-[var(--ink)]">Age</dt>
                <dd>{looks.age ?? "—"}</dd>
              </div>
              <div>
                <dt className="font-semibold text-[var(--ink)]">Appearance</dt>
                <dd>
                  {[looks.ethnicity, looks.hair_color, looks.hair_style, looks.eye_color, looks.style]
                    .filter(Boolean)
                    .join(" · ") || "—"}
                </dd>
              </div>
              {bodyEntries(looks.body).map(([k, v]) => (
                <div key={k}>
                  <dt className="font-semibold capitalize text-[var(--ink)]">
                    {k.replace(/_/g, " ")}
                  </dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="muted mt-2 text-sm">No looks data.</p>
          )}
        </div>
      </div>

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-2xl tracking-tight">Generated content</h2>
            <p className="muted text-sm">Everything this influencer has produced.</p>
          </div>
          <Link className="btn secondary" to={`/history?influencer=${inf.id}`}>
            Open in Library
          </Link>
        </div>

        {!items.length ? (
          <div className="panel">
            <p className="muted text-sm">No posts yet.</p>
            <button className="btn mt-3" onClick={() => tryIdentity.mutate()}>
              Generate identity shot
            </button>
          </div>
        ) : (
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
        )}
      </section>

      <ImageLightbox
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected ? `Generation #${selected.id}` : ""}
        subtitle={selected ? `Seed ${selected.seed ?? "—"} · ${selected.model_used}` : undefined}
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
            : (selected?.status ?? "No image")
        }
      >
        {selected && (
          <>
            <p className="line-clamp-4 text-sm">{selected.expanded_prompt}</p>
            <div className="flex flex-wrap gap-3">
              {!selected.is_nsfw && !selected.is_vaulted && selected.status === "completed" && (
                <button
                  className="btn"
                  disabled={lockFace.isPending}
                  onClick={() => lockFace.mutate(selected.id)}
                >
                  Lock this face
                </button>
              )}
              <button className="btn secondary" onClick={() => regenerate.mutate(selected.id)}>
                Regenerate
              </button>
              <Link className="btn secondary" to={`/history?influencer=${inf.id}`}>
                Open in Library
              </Link>
            </div>
          </>
        )}
      </ImageLightbox>
    </div>
  );
}
