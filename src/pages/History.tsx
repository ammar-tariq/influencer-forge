import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, mediaUrl, vaultRevealUrl } from "../api/client";
import { BackLink } from "../components/common/BackLink";
import { GenerationCard } from "../components/common/GenerationCard";
import { ImageLightbox } from "../components/common/ImageLightbox";
import { PinPrompt } from "../components/common/PinPrompt";
import { StatusBadge } from "../components/common/StatusBadge";
import { useVaultReveal } from "../hooks/useVaultReveal";
import type { Generation } from "../types";

export function History() {
  const qc = useQueryClient();
  const reveal = useVaultReveal();
  const [params, setParams] = useSearchParams();
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const vaultStatus = useQuery({ queryKey: ["vault-status"], queryFn: api.vaultStatus });
  const initialInf = params.get("influencer");
  const [influencerId, setInfluencerId] = useState<number | "">(
    initialInf && Number(initialInf) ? Number(initialInf) : "",
  );
  const [nsfw, setNsfw] = useState<"all" | "sfw" | "nsfw">("all");
  const [selected, setSelected] = useState<Generation | null>(null);
  const [deleteArmed, setDeleteArmed] = useState(false);
  const [watermark, setWatermark] = useState("");
  const [overlay, setOverlay] = useState("");
  const [cropX1, setCropX1] = useState("");
  const [cropY1, setCropY1] = useState("");
  const [cropX2, setCropX2] = useState("");
  const [cropY2, setCropY2] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

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
    // Always face-lock on Library regenerate when a Face Seed exists (server also defaults).
    mutationFn: (id: number) => api.regenerate(id, { identity_explore: false }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["generations"] }),
  });

  const removePost = useMutation({
    mutationFn: (id: number) => api.deleteGeneration(id),
    onSuccess: async () => {
      setSelected(null);
      setDeleteArmed(false);
      if (reveal.viewUnlocked) await reveal.endReveal();
      await qc.invalidateQueries({ queryKey: ["generations"] });
    },
  });

  const editPost = useMutation({
    mutationFn: (body: {
      generation_id: number;
      rotate_degrees?: number;
      crop?: [number, number, number, number];
      watermark_text?: string;
      overlay_text?: string;
    }) => api.postProcess(body),
    onSuccess: async (_out, vars) => {
      setEditError(null);
      const fresh = await api.getGeneration(vars.generation_id);
      setSelected(fresh);
      await qc.invalidateQueries({ queryKey: ["generations"] });
    },
    onError: (err: Error) => setEditError(err.message),
  });

  async function imageSize(url: string): Promise<{ w: number; h: number }> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight });
      img.onerror = () => reject(new Error("Could not load image size"));
      img.src = url;
    });
  }

  async function cropMarginPercent(percent: number, src: string, generationId: number) {
    try {
      setEditError(null);
      const { w, h } = await imageSize(src);
      const mx = Math.floor(w * percent);
      const my = Math.floor(h * percent);
      if (w - 2 * mx < 8 || h - 2 * my < 8) {
        setEditError("Crop too aggressive for this image size");
        return;
      }
      editPost.mutate({
        generation_id: generationId,
        crop: [mx, my, w - mx, h - my],
      });
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Crop failed");
    }
  }

  function applyManualCrop(generationId: number) {
    const x1 = Number(cropX1);
    const y1 = Number(cropY1);
    const x2 = Number(cropX2);
    const y2 = Number(cropY2);
    if (![x1, y1, x2, y2].every((n) => Number.isFinite(n)) || x2 <= x1 || y2 <= y1) {
      setEditError("Crop needs x1,y1,x2,y2 with x2>x1 and y2>y1");
      return;
    }
    setEditError(null);
    editPost.mutate({
      generation_id: generationId,
      crop: [Math.round(x1), Math.round(y1), Math.round(x2), Math.round(y2)],
    });
  }

  const browseUnlocked = Boolean(vaultStatus.data?.unlocked);
  const pendingNsfw = vaultStatus.data?.pending_nsfw ?? 0;
  const hiddenVaulted = useMemo(() => {
    if (browseUnlocked) return 0;
    return (generations.data ?? []).filter((g) => g.is_vaulted).length;
  }, [generations.data, browseUnlocked]);
  // When vault is off, hide vaulted NSFW from the Library entirely.
  const items = useMemo(() => {
    const all = generations.data ?? [];
    if (browseUnlocked) return all;
    return all.filter((g) => !g.is_vaulted);
  }, [generations.data, browseUnlocked]);
  const selectedIndex = selected ? items.findIndex((g) => g.id === selected.id) : -1;
  const hasPrev = selectedIndex > 0;
  const hasNext = selectedIndex >= 0 && selectedIndex < items.length - 1;

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
    setDeleteArmed(false);
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

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackLink
          fallbackTo={influencerId !== "" ? `/influencers/${influencerId}` : "/influencers"}
          label="Back"
        />
      </div>
      <header>
        <h1 className="text-3xl tracking-tight">Library</h1>
        <p className="muted mt-1">
          Generated posts
          {influencerId !== ""
            ? ` for ${influencers.data?.find((i) => i.id === influencerId)?.name ?? `#${influencerId}`}`
            : ""}
          .
        </p>
      </header>

      {pendingNsfw > 0 && (
        <div className="panel border-[var(--accent-2)]">
          <p className="text-sm">
            {pendingNsfw} NSFW generation{pendingNsfw === 1 ? "" : "s"} waiting to encrypt. Turn on{" "}
            <strong>Privacy vault</strong> in the sidebar — they move in automatically.
          </p>
        </div>
      )}
      {!browseUnlocked && hiddenVaulted > 0 && (
        <p className="muted text-sm">
          {hiddenVaulted} vaulted post{hiddenVaulted === 1 ? "" : "s"} hidden. Turn on Privacy vault
          in the sidebar to show blur teasers.
        </p>
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
            onClick={() => openPost(g)}
          />
        ))}
      </div>

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
        title={selected ? `Generation #${selected.id}` : ""}
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
              ? `${detailSrc}?t=${selected.id}-${reveal.viewUnlocked ? "1" : "0"}`
              : detailSrc
            : null
        }
        isVideo={Boolean(selected?.output_path?.match(/\.(mp4|webm|mov)$/i))}
        placeholder={`${selected?.status ?? ""}${selected?.error_message ? ` — ${selected.error_message}` : ""}`}
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
              <button className="btn" onClick={() => regenerate.mutate(selected.id)}>
                Regenerate
              </button>
              {detailSrc && !selected.is_vaulted && (
                <a className="btn secondary" href={detailSrc} target="_blank" rel="noreferrer">
                  Open in new tab
                </a>
              )}
              {!deleteArmed ? (
                <button
                  className="btn secondary"
                  disabled={removePost.isPending || selected.status === "queued" || selected.status === "running"}
                  onClick={() => setDeleteArmed(true)}
                >
                  Delete post
                </button>
              ) : (
                <>
                  <button
                    className="btn"
                    style={{ background: "var(--danger)", color: "#1a0a0a" }}
                    disabled={removePost.isPending}
                    onClick={() => removePost.mutate(selected.id)}
                  >
                    {removePost.isPending ? "Deleting…" : "Yes, delete post"}
                  </button>
                  <button
                    className="btn secondary"
                    disabled={removePost.isPending}
                    onClick={() => setDeleteArmed(false)}
                  >
                    Cancel
                  </button>
                </>
              )}
              {selected.is_nsfw && !selected.is_vaulted && (
                <p className="muted text-xs">
                  NSFW auto-vaults when Privacy vault is on
                  {browseUnlocked ? "…" : " — enable it in the sidebar to encrypt pending items."}
                </p>
              )}
            </div>
            {selected.status === "completed" &&
              !selected.is_vaulted &&
              !selected.output_path?.match(/\.(mp4|webm|mov)$/i) && (
                <div className="mt-4 space-y-2 border-t border-[var(--line)] pt-3">
                  <p className="text-sm font-semibold">Edit image</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      className="btn secondary"
                      disabled={editPost.isPending}
                      onClick={() =>
                        editPost.mutate({ generation_id: selected.id, rotate_degrees: -90 })
                      }
                    >
                      Rotate left
                    </button>
                    <button
                      className="btn secondary"
                      disabled={editPost.isPending}
                      onClick={() =>
                        editPost.mutate({ generation_id: selected.id, rotate_degrees: 90 })
                      }
                    >
                      Rotate right
                    </button>
                    {detailSrc && (
                      <>
                        <button
                          className="btn secondary"
                          disabled={editPost.isPending}
                          onClick={() => void cropMarginPercent(0.1, detailSrc, selected.id)}
                        >
                          Crop 10% margins
                        </button>
                        <button
                          className="btn secondary"
                          disabled={editPost.isPending}
                          onClick={() => void cropMarginPercent(0.2, detailSrc, selected.id)}
                        >
                          Crop 20% margins
                        </button>
                      </>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <div className="field">
                      <label>x1</label>
                      <input value={cropX1} onChange={(e) => setCropX1(e.target.value)} inputMode="numeric" />
                    </div>
                    <div className="field">
                      <label>y1</label>
                      <input value={cropY1} onChange={(e) => setCropY1(e.target.value)} inputMode="numeric" />
                    </div>
                    <div className="field">
                      <label>x2</label>
                      <input value={cropX2} onChange={(e) => setCropX2(e.target.value)} inputMode="numeric" />
                    </div>
                    <div className="field">
                      <label>y2</label>
                      <input value={cropY2} onChange={(e) => setCropY2(e.target.value)} inputMode="numeric" />
                    </div>
                  </div>
                  <button
                    className="btn secondary"
                    disabled={editPost.isPending}
                    onClick={() => applyManualCrop(selected.id)}
                  >
                    Apply crop
                  </button>
                  <div className="field">
                    <label>Watermark</label>
                    <input
                      value={watermark}
                      onChange={(e) => setWatermark(e.target.value)}
                      placeholder="© your brand"
                    />
                  </div>
                  <div className="field">
                    <label>Top overlay</label>
                    <input
                      value={overlay}
                      onChange={(e) => setOverlay(e.target.value)}
                      placeholder="Optional caption"
                    />
                  </div>
                  <button
                    className="btn"
                    disabled={editPost.isPending || (!watermark.trim() && !overlay.trim())}
                    onClick={() =>
                      editPost.mutate({
                        generation_id: selected.id,
                        watermark_text: watermark.trim() || undefined,
                        overlay_text: overlay.trim() || undefined,
                      })
                    }
                  >
                    {editPost.isPending ? "Applying…" : "Apply text"}
                  </button>
                  {editError && <p className="text-sm text-[var(--danger)]">{editError}</p>}
                </div>
              )}
          </>
        )}
      </ImageLightbox>
    </div>
  );
}
