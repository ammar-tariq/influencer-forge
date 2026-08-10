import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";

type Props = {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  /** Full image or video URL, or null to show placeholder message */
  imageSrc?: string | null;
  /** Force video player (otherwise inferred from .mp4/.webm) */
  isVideo?: boolean;
  placeholder?: string;
  children?: ReactNode;
};

function looksLikeVideo(src?: string | null) {
  if (!src) return false;
  return /\.(mp4|webm|mov)(\?|$)/i.test(src);
}

export function ImageLightbox({
  open,
  onClose,
  title,
  subtitle,
  imageSrc,
  isVideo,
  placeholder = "No image",
  children,
}: Props) {
  const video = Boolean(isVideo || looksLikeVideo(imageSrc));
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      className="lightbox-root"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
    >
      <div className="lightbox-panel" onClick={(e) => e.stopPropagation()}>
        <header className="lightbox-header">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold tracking-tight">{title}</h2>
            {subtitle && <p className="muted mt-0.5 truncate text-sm">{subtitle}</p>}
          </div>
          <button type="button" className="btn secondary shrink-0" onClick={onClose}>
            Close
          </button>
        </header>

        <div className="lightbox-stage">
          {imageSrc && video ? (
            <video
              key={imageSrc}
              src={imageSrc}
              className="lightbox-image"
              controls
              autoPlay
              loop
              playsInline
            />
          ) : imageSrc ? (
            <img src={imageSrc} alt={title} className="lightbox-image" />
          ) : (
            <p className="muted px-6 text-center text-sm">{placeholder}</p>
          )}
        </div>

        {children && <footer className="lightbox-footer">{children}</footer>}
      </div>
    </div>,
    document.body,
  );
}
