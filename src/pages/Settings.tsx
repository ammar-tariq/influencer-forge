import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, setMediaEpoch } from "../api/client";
import { useSystemStats } from "../hooks/useSystemStats";

function settingMap(items: { key: string; value: string }[] | undefined) {
  return Object.fromEntries((items ?? []).map((s) => [s.key, s.value]));
}

export function Settings() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.listSettings });
  const map = settingMap(settings.data);
  const { data: stats } = useSystemStats();
  const comfy = useQuery({
    queryKey: ["comfy-status"],
    queryFn: api.comfyStatus,
    refetchInterval: 3000,
  });
  const pause = useMutation({ mutationFn: api.pauseQueue });
  const resume = useMutation({ mutationFn: api.resumeQueue });
  const [confirmText, setConfirmText] = useState("");
  const [includeModels, setIncludeModels] = useState(false);
  const [armed, setArmed] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);

  const confirmOk = confirmText.trim().toUpperCase() === "RESET";

  const save = useMutation({
    mutationFn: async (form: FormData) => {
      await api.putSetting("llm_provider", String(form.get("llm_provider") ?? "local"));
      await api.putSetting("openai_api_key", String(form.get("openai_api_key") ?? ""));
      await api.putSetting("anthropic_api_key", String(form.get("anthropic_api_key") ?? ""));
      await api.putSetting("gemini_api_key", String(form.get("gemini_api_key") ?? ""));
      await api.putSetting("image_model", "stub_or_sdxl");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  const reset = useMutation({
    mutationFn: () => api.fullReset(includeModels),
    onSuccess: async (res) => {
      setConfirmText("");
      setArmed(false);
      setResetMessage(`Reset complete. Data dir: ${res.data_dir}`);
      setMediaEpoch(res.media_epoch ?? Date.now());
      // Drop stale lists so Studio/Library don't keep showing wiped influencers.
      qc.clear();
      await qc.invalidateQueries();
      navigate("/", { replace: true });
    },
    onError: (err: Error) => {
      setArmed(false);
      setResetMessage(err.message);
    },
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Settings</h1>
        <p className="muted mt-1">Keys stay on this machine. No telemetry.</p>
      </header>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl tracking-tight">System</h2>
          <p className="muted text-sm">Live CPU/RAM, queue pressure, and ComfyUI health.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="panel">
            <div className="muted text-sm">CPU</div>
            <div className="mt-2 text-3xl">{stats?.cpu_percent?.toFixed(0) ?? "—"}%</div>
          </div>
          <div className="panel">
            <div className="muted text-sm">RAM</div>
            <div className="mt-2 text-3xl">{stats?.ram_percent?.toFixed(0) ?? "—"}%</div>
            <div className="muted mt-1 text-xs">
              {stats ? `${stats.ram_used_gb}/${stats.ram_total_gb} GB` : ""}
            </div>
          </div>
          <div className="panel">
            <div className="muted text-sm">Queue</div>
            <div className="mt-2 text-3xl">
              {stats ? `${stats.queue_pending}/${stats.queue_processing}` : "—"}
            </div>
          </div>
        </div>
        <div className="panel">
          <h3 className="text-lg">ComfyUI</h3>
          <p className="muted mt-2 text-sm">
            enabled={String(comfy.data?.enabled ?? false)} · healthy=
            {String(comfy.data?.healthy ?? false)} · process=
            {String(comfy.data?.process_running ?? false)}
          </p>
          <p className="muted mt-1 text-xs">{comfy.data?.url}</p>
        </div>
        <div className="panel flex gap-3">
          <button type="button" className="btn secondary" onClick={() => pause.mutate()}>
            Pause queue
          </button>
          <button type="button" className="btn" onClick={() => resume.mutate()}>
            Resume queue
          </button>
        </div>
      </section>

      <form
        className="panel"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(new FormData(e.currentTarget));
        }}
      >
        <h2 className="mb-3 text-lg">Model providers</h2>
        <div className="field">
          <label>LLM provider</label>
          <select name="llm_provider" defaultValue={map.llm_provider ?? "local"} key={map.llm_provider ?? "local"}>
            <option value="local">Local (template / llama)</option>
            <option value="openai">OpenAI</option>
            <option value="claude">Claude</option>
            <option value="gemini">Gemini</option>
          </select>
        </div>
        <div className="field">
          <label>OpenAI API key</label>
          <input name="openai_api_key" defaultValue={map.openai_api_key ?? ""} key={`o-${map.openai_api_key ?? ""}`} />
        </div>
        <div className="field">
          <label>Anthropic API key</label>
          <input
            name="anthropic_api_key"
            defaultValue={map.anthropic_api_key ?? ""}
            key={`a-${map.anthropic_api_key ?? ""}`}
          />
        </div>
        <div className="field">
          <label>Gemini API key</label>
          <input name="gemini_api_key" defaultValue={map.gemini_api_key ?? ""} key={`g-${map.gemini_api_key ?? ""}`} />
        </div>
        <button className="btn" type="submit">
          Save settings
        </button>
      </form>

      <div className="panel border-[color-mix(in_srgb,var(--danger)_35%,var(--line))]">
        <h2 className="text-lg text-[var(--danger)]">Full reset</h2>
        <p className="muted mt-2 text-sm">
          Deletes the local database, generations, thumbnails, uploads, vault data, and schedules.
          Does <strong>not</strong> delete ComfyUI or `/Volumes/external/hfModels`.
        </p>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeModels}
            onChange={(e) => setIncludeModels(e.target.checked)}
          />
          Also wipe app-data `models/` cache (not hfModels)
        </label>
        <div className="field mt-4">
          <label>Type RESET to confirm</label>
          <input
            value={confirmText}
            onChange={(e) => {
              setConfirmText(e.target.value);
              setArmed(false);
            }}
            placeholder="RESET"
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        {resetMessage && (
          <p
            className={`mb-3 text-sm ${
              reset.isError ? "text-[var(--danger)]" : "text-[var(--accent)]"
            }`}
          >
            {resetMessage}
          </p>
        )}
        {/* Native window.confirm is a silent no-op in macOS Tauri WKWebView — use in-app arming. */}
        {!armed ? (
          <button
            className="btn"
            type="button"
            style={{ background: "var(--danger)", color: "#1a0a0a" }}
            disabled={!confirmOk || reset.isPending}
            onClick={() => setArmed(true)}
          >
            Reset all local data
          </button>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm text-[var(--danger)]">Erase everything now?</p>
            <button
              className="btn"
              type="button"
              style={{ background: "var(--danger)", color: "#1a0a0a" }}
              disabled={reset.isPending}
              onClick={() => reset.mutate()}
            >
              {reset.isPending ? "Resetting…" : "Yes, erase all data"}
            </button>
            <button
              className="btn secondary"
              type="button"
              disabled={reset.isPending}
              onClick={() => setArmed(false)}
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
