import { useState } from "react";
import { mediaUrl } from "../../api/client";

type Props = {
  path?: string | null;
  alt?: string;
  className?: string;
  fallback?: string;
};

/** Renders an image from an orchestrator disk path via /media/... */
export function MediaImage({ path, alt = "", className, fallback = "No image yet" }: Props) {
  const src = mediaUrl(path);
  const [failed, setFailed] = useState(false);

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

  return (
    <img
      src={src}
      alt={alt}
      className={className ?? "h-40 w-full rounded-xl object-cover"}
      onError={() => setFailed(true)}
    />
  );
}
