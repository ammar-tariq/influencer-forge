import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { SCHEDULE_FREQUENCIES } from "../constants/options";

export function Scheduler() {
  const qc = useQueryClient();
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const schedules = useQuery({ queryKey: ["schedules"], queryFn: api.listSchedules });
  const [influencerId, setInfluencerId] = useState<number | "">("");
  const [time, setTime] = useState("09:00");
  const [frequency, setFrequency] = useState("daily");
  const [cron, setCron] = useState("");
  const [template, setTemplate] = useState("Good morning! Today I'm wearing {wardrobe} in a {scene}.");

  const create = useMutation({
    mutationFn: () =>
      api.createSchedule({
        influencer_id: Number(influencerId),
        schedule_time: time.length === 5 ? `${time}:00` : time,
        frequency,
        prompt_template: template,
        ...(frequency === "custom" && cron.trim() ? { cron_expression: cron.trim() } : {}),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Scheduler</h1>
        <p className="muted mt-1">Reminders to generate. Calendar sync IDs can be attached later.</p>
      </header>
      <div className="panel">
        <div className="field">
          <label>Influencer</label>
          <select value={influencerId} onChange={(e) => setInfluencerId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Select…</option>
            {(influencers.data ?? []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Time</label>
          <input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </div>
        <div className="field">
          <label>Frequency</label>
          <select value={frequency} onChange={(e) => setFrequency(e.target.value)}>
            {SCHEDULE_FREQUENCIES.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        </div>
        {frequency === "custom" && (
          <div className="field">
            <label>Custom cron / notes</label>
            <input
              value={cron}
              onChange={(e) => setCron(e.target.value)}
              placeholder="e.g. 0 9 * * 1-5 (weekdays 9:00)"
            />
          </div>
        )}
        <div className="field">
          <label>Prompt template</label>
          <textarea rows={3} value={template} onChange={(e) => setTemplate(e.target.value)} />
        </div>
        <button className="btn" disabled={!influencerId} onClick={() => create.mutate()}>
          Add schedule
        </button>
      </div>
      <div className="space-y-3">
        {(schedules.data ?? []).map((s) => (
          <div key={s.id} className="panel">
            <div className="font-semibold">
              #{s.id} · influencer {s.influencer_id} · {s.schedule_time} ({s.frequency})
            </div>
            <p className="muted mt-1 text-sm">{s.prompt_template}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
