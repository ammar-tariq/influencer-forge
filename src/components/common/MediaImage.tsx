import { useEffect, useState } from "react";
import { mediaUrl } from "../../api/client";

type Props = {
  path?: string | null;
  alt?: string;
  className?: string;
  fallback?: string;
  /** Force <video>; otherwise inferred from extension */
  isVideo?: boolean;
  /** Extra cache key (e.g. completed_at) when the same path gets new bytes */
  cacheKey?: string | number | null;
};

function looksLikeVideo(path?: string | null) {
  if (!path) return false;
  return /\.(mp4|webm|mov)(\?|$)/i.test(path.replace(/\\/g, "/"));
}

/** Renders an image or video from an orchestrator disk path via /media/... */
export function MediaImage({
  path,
  alt = "",
  className,
  fallback = "No image yet",
  isVideo,
  cacheKey,
}: Props) {
  const baseSrc = mediaUrl(path);
  const src =
    baseSrc && cacheKey != null && cacheKey !== ""
      ? `${baseSrc}${baseSrc.includes("?") ? "&" : "?"}k=${encodeURIComponent(String(cacheKey))}`
      : baseSrc;
  const [failed, setFailed] = useState(false);
  const video = Boolean(isVideo || looksLikeVideo(path) || looksLikeVideo(src));

  useEffect(() => {
    setFailed(false);
  }, [src]);

  if (!src || failed) {
    return (
      <div
        className={
          className ??
          "flex h-40 items-center justify-center rounded-xl bg-[var(--bg2)] text-sm muted"
        }
      >
        {fallback}
      </div>
    );
  }

  if (video) {
    return (
      <video
        key={src}
        src={src}
        className={className ?? "h-40 w-full rounded-xl object-cover"}
        controls
        muted
        loop
        playsInline
        onError={() => setFailed(true)}
      />
    );
  }

  return (
    <img
      key={src}
      src={src}
      alt={alt}
      className={className ?? "h-40 w-full rounded-xl object-cover"}
      onError={() => setFailed(true)}
    />
  );
}
