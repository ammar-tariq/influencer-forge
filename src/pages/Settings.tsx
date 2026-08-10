import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function Settings() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.listSettings });
  const [provider, setProvider] = useState("local");
  const [openai, setOpenai] = useState("");
  const [anthropic, setAnthropic] = useState("");
  const [gemini, setGemini] = useState("");

  useEffect(() => {
    const map = Object.fromEntries((settings.data ?? []).map((s) => [s.key, s.value]));
    if (map.llm_provider) setProvider(map.llm_provider);
    if (map.openai_api_key) setOpenai(map.openai_api_key);
    if (map.anthropic_api_key) setAnthropic(map.anthropic_api_key);
    if (map.gemini_api_key) setGemini(map.gemini_api_key);
  }, [settings.data]);

  const save = useMutation({
    mutationFn: async () => {
      await api.putSetting("llm_provider", provider);
      await api.putSetting("openai_api_key", openai);
      await api.putSetting("anthropic_api_key", anthropic);
      await api.putSetting("gemini_api_key", gemini);
      await api.putSetting("image_model", "stub_or_sdxl");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Model settings</h1>
        <p className="muted mt-1">Keys stay on this machine. No telemetry.</p>
      </header>
      <div className="panel">
        <div className="field">
          <label>LLM provider</label>
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="local">Local (template / llama)</option>
            <option value="openai">OpenAI</option>
            <option value="claude">Claude</option>
            <option value="gemini">Gemini</option>
          </select>
        </div>
        <div className="field">
          <label>OpenAI API key</label>
          <input value={openai} onChange={(e) => setOpenai(e.target.value)} />
        </div>
        <div className="field">
          <label>Anthropic API key</label>
          <input value={anthropic} onChange={(e) => setAnthropic(e.target.value)} />
        </div>
        <div className="field">
          <label>Gemini API key</label>
          <input value={gemini} onChange={(e) => setGemini(e.target.value)} />
        </div>
        <button className="btn" onClick={() => save.mutate()}>
          Save settings
        </button>
      </div>
    </div>
  );
}
