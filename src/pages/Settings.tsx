import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

function settingMap(items: { key: string; value: string }[] | undefined) {
  return Object.fromEntries((items ?? []).map((s) => [s.key, s.value]));
}

export function Settings() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.listSettings });
  const map = settingMap(settings.data);
  const [confirmText, setConfirmText] = useState("");
  const [includeModels, setIncludeModels] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);

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
    onSuccess: (res) => {
      setConfirmText("");
      setResetMessage(`Reset complete. Data dir: ${res.data_dir}`);
      void qc.invalidateQueries();
    },
    onError: (err: Error) => setResetMessage(err.message),
  });

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Settings</h1>
        <p className="muted mt-1">Keys stay on this machine. No telemetry.</p>
      </header>
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
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="RESET"
            autoComplete="off"
          />
        </div>
        {resetMessage && <p className="mb-3 text-sm text-[var(--accent)]">{resetMessage}</p>}
        <button
          className="btn"
          type="button"
          style={{ background: "var(--danger)", color: "#1a0a0a" }}
          disabled={confirmText !== "RESET" || reset.isPending}
          onClick={() => {
            if (window.confirm("This permanently erases local InfluencerForge data. Continue?")) {
              reset.mutate();
            }
          }}
        >
          {reset.isPending ? "Resetting…" : "Reset all local data"}
        </button>
      </div>
    </div>
  );
}
