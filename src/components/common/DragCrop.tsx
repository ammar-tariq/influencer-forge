import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";

type Props = {
  src: string;
  disabled?: boolean;
  onCrop: (box: [number, number, number, number]) => void;
};

type Point = { x: number; y: number };

/** Drag a rectangle on the preview; emits natural-image pixel coords. */
export function DragCrop({ src, disabled, onCrop }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [origin, setOrigin] = useState<Point | null>(null);
  const [current, setCurrent] = useState<Point | null>(null);

  function clientToLocal(e: ReactPointerEvent): Point | null {
    const el = wrapRef.current;
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
      x: Math.min(Math.max(0, e.clientX - r.left), r.width),
      y: Math.min(Math.max(0, e.clientY - r.top), r.height),
    };
  }

  function onPointerDown(e: ReactPointerEvent) {
    if (disabled) return;
    const p = clientToLocal(e);
    if (!p) return;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    setOrigin(p);
    setCurrent(p);
  }

  function onPointerMove(e: ReactPointerEvent) {
    if (!origin || disabled) return;
    const p = clientToLocal(e);
    if (p) setCurrent(p);
  }

  function onPointerUp() {
    if (!origin || !current || !imgRef.current || !wrapRef.current) {
      setOrigin(null);
      setCurrent(null);
      return;
    }
    const img = imgRef.current;
    const wrap = wrapRef.current.getBoundingClientRect();
    const nw = img.naturalWidth || 1;
    const nh = img.naturalHeight || 1;
    const sx = nw / Math.max(wrap.width, 1);
    const sy = nh / Math.max(wrap.height, 1);
    const x1 = Math.round(Math.min(origin.x, current.x) * sx);
    const y1 = Math.round(Math.min(origin.y, current.y) * sy);
    const x2 = Math.round(Math.max(origin.x, current.x) * sx);
    const y2 = Math.round(Math.max(origin.y, current.y) * sy);
    setOrigin(null);
    setCurrent(null);
    if (x2 - x1 < 8 || y2 - y1 < 8) return;
    onCrop([x1, y1, x2, y2]);
  }

  const box =
    origin && current
      ? {
          left: Math.min(origin.x, current.x),
          top: Math.min(origin.y, current.y),
          width: Math.abs(current.x - origin.x),
          height: Math.abs(current.y - origin.y),
        }
      : null;

  return (
    <div className="space-y-1">
      <p className="muted text-xs">Drag on the preview to crop (applies on release).</p>
      <div
        ref={wrapRef}
        className="drag-crop relative max-h-56 w-full max-w-sm overflow-hidden rounded border border-[var(--line)]"
        style={{ touchAction: "none", cursor: disabled ? "default" : "crosshair" }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        <img
          ref={imgRef}
          src={src}
          alt="Crop preview"
          className="block max-h-56 w-full select-none object-contain"
          draggable={false}
        />
        {box && (
          <div
            className="pointer-events-none absolute border-2 border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_18%,transparent)]"
            style={{
              left: box.left,
              top: box.top,
              width: box.width,
              height: box.height,
            }}
          />
        )}
      </div>
    </div>
  );
}
