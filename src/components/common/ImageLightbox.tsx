import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { IconChevronLeft, IconChevronRight } from "./icons";

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
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
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
  onPrev,
  onNext,
  hasPrev = false,
  hasNext = false,
}: Props) {
  const video = Boolean(isVideo || looksLikeVideo(imageSrc));
  const showNav = Boolean(onPrev || onNext);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "ArrowLeft" && hasPrev && onPrev) {
        e.preventDefault();
        onPrev();
      }
      if (e.key === "ArrowRight" && hasNext && onNext) {
        e.preventDefault();
        onNext();
      }
    };
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose, onPrev, onNext, hasPrev, hasNext]);

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
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-lg font-semibold tracking-tight">{title}</h2>
            {subtitle && <p className="muted mt-0.5 truncate text-sm">{subtitle}</p>}
          </div>
          <button type="button" className="btn secondary shrink-0" onClick={onClose}>
            Close
          </button>
        </header>

        <div className="lightbox-stage">
          {showNav && (
            <button
              type="button"
              className="lightbox-nav lightbox-nav-prev"
              aria-label="Previous"
              disabled={!hasPrev}
              onClick={onPrev}
            >
              <IconChevronLeft size={22} />
            </button>
          )}

          <div className="lightbox-media">
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

          {showNav && (
            <button
              type="button"
              className="lightbox-nav lightbox-nav-next"
              aria-label="Next"
              disabled={!hasNext}
              onClick={onNext}
            >
              <IconChevronRight size={22} />
            </button>
          )}
        </div>

        {children && <footer className="lightbox-footer">{children}</footer>}
      </div>
    </div>,
    document.body,
  );
}
