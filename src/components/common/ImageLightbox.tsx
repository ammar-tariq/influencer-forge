import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";

type Props = {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  /** Full image URL, or null to show placeholder message */
  imageSrc?: string | null;
  placeholder?: string;
  children?: ReactNode;
};

export function ImageLightbox({
  open,
  onClose,
  title,
  subtitle,
  imageSrc,
  placeholder = "No image",
  children,
}: Props) {
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
          {imageSrc ? (
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
