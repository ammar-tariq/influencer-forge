import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function Post() {
  const generations = useQuery({ queryKey: ["generations"], queryFn: () => api.listGenerations() });
  const [id, setId] = useState<number | "">("");
  const [watermark, setWatermark] = useState("InfluencerForge");
  const [overlay, setOverlay] = useState("");
  const [rotate, setRotate] = useState(0);
  const [result, setResult] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: () =>
      api.postProcess({
        generation_id: Number(id),
        rotate_degrees: rotate,
        watermark_text: watermark || undefined,
        overlay_text: overlay || undefined,
      }),
    onSuccess: (res) => setResult(res.output_path),
  });

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Post-production</h1>
        <p className="muted mt-1">Crop/rotate/watermark helpers via Pillow.</p>
      </header>
      <div className="panel">
        <div className="field">
          <label>Generation</label>
          <select value={id} onChange={(e) => setId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Select…</option>
            {(generations.data ?? [])
              .filter((g) => g.status === "completed")
              .map((g) => (
                <option key={g.id} value={g.id}>
                  #{g.id} · {g.user_prompt.slice(0, 40)}
                </option>
              ))}
          </select>
        </div>
        <div className="field">
          <label>Rotate degrees</label>
          <input type="number" value={rotate} onChange={(e) => setRotate(Number(e.target.value))} />
        </div>
        <div className="field">
          <label>Watermark</label>
          <input value={watermark} onChange={(e) => setWatermark(e.target.value)} />
        </div>
        <div className="field">
          <label>Overlay text</label>
          <input value={overlay} onChange={(e) => setOverlay(e.target.value)} />
        </div>
        <button className="btn" disabled={!id} onClick={() => run.mutate()}>
          Apply edits
        </button>
        {result && <p className="muted mt-3 text-sm">Wrote {result}</p>}
      </div>
    </div>
  );
}
