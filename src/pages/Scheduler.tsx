import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { SCHEDULE_FREQUENCIES } from "../constants/options";

export function Scheduler() {
  const qc = useQueryClient();
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const schedules = useQuery({ queryKey: ["schedules"], queryFn: api.listSchedules });
  const reminders = useQuery({
    queryKey: ["reminders"],
    queryFn: api.reminders,
    refetchInterval: 15000,
  });
  const [influencerId, setInfluencerId] = useState<number | "">("");
  const [time, setTime] = useState("09:00");
  const [frequency, setFrequency] = useState("daily");
  const [cron, setCron] = useState("");
  const [template, setTemplate] = useState(
    "full body shot, standing naturally, wearing casual everyday outfit, soft daylight",
  );
  const [message, setMessage] = useState<string | null>(null);

  const nameFor = (id: number) =>
    influencers.data?.find((i) => i.id === id)?.name ?? `Influencer #${id}`;

  const create = useMutation({
    mutationFn: () =>
      api.createSchedule({
        influencer_id: Number(influencerId),
        schedule_time: time.length === 5 ? `${time}:00` : time,
        frequency,
        prompt_template: template,
        ...(frequency === "custom" && cron.trim() ? { cron_expression: cron.trim() } : {}),
      }),
    onSuccess: () => {
      setMessage("Schedule added");
      void qc.invalidateQueries({ queryKey: ["schedules"] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const toggle = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      api.patchSchedule(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteSchedule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });

  const due = reminders.data?.reminders ?? [];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Scheduler</h1>
        <p className="muted mt-1">
          Local reminders to create posts. Calendar sync is not wired yet — due items show here and
          on Studio home.
        </p>
      </header>

      {due.length > 0 && (
        <div className="panel border-[var(--accent-2)] space-y-3">
          <h2 className="text-lg">Due now ({due.length})</h2>
          {due.map((r, idx) => {
            const rem = r as {
              schedule_id?: number;
              influencer_id?: number;
              prompt_template?: string;
            };
            return (
              <div key={`${rem.schedule_id ?? idx}`} className="flex flex-wrap items-center gap-3">
                <p className="text-sm min-w-0 flex-1">
                  <span className="font-semibold">
                    {nameFor(Number(rem.influencer_id ?? 0))}
                  </span>
                  <span className="muted"> — {(rem.prompt_template || "").slice(0, 80)}</span>
                </p>
                <Link
                  className="btn"
                  to="/generate"
                  state={{
                    createdId: rem.influencer_id,
                    schedulePrompt: rem.prompt_template,
                  }}
                >
                  Create post
                </Link>
              </div>
            );
          })}
        </div>
      )}

      <div className="panel">
        <div className="field">
          <label>Influencer</label>
          <select
            value={influencerId}
            onChange={(e) => setInfluencerId(e.target.value ? Number(e.target.value) : "")}
          >
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
              placeholder="Stored for later cron support (daily/weekly/monthly run by time today)"
            />
          </div>
        )}
        <div className="field">
          <label>Prompt template</label>
          <textarea rows={3} value={template} onChange={(e) => setTemplate(e.target.value)} />
          <p className="muted mt-1 text-xs">Used as the scene notes when you open Create post from a reminder.</p>
        </div>
        <button
          className="btn"
          disabled={!influencerId || create.isPending}
          onClick={() => create.mutate()}
        >
          {create.isPending ? "Saving…" : "Add schedule"}
        </button>
        {message && <p className="mt-3 text-sm text-[var(--accent-2)]">{message}</p>}
      </div>

      <div className="space-y-3">
        {(schedules.data ?? []).length === 0 && (
          <p className="muted text-sm">No schedules yet.</p>
        )}
        {(schedules.data ?? []).map((s) => (
          <div key={s.id} className="panel">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="font-semibold">
                  {nameFor(s.influencer_id)} · {s.schedule_time} ({s.frequency})
                  {!s.is_active ? " · paused" : ""}
                </div>
                <p className="muted mt-1 text-sm">{s.prompt_template}</p>
                {s.next_trigger && (
                  <p className="muted mt-1 text-xs">Next: {s.next_trigger}</p>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className="btn secondary"
                  disabled={toggle.isPending}
                  onClick={() => toggle.mutate({ id: s.id, is_active: !s.is_active })}
                >
                  {s.is_active ? "Pause" : "Resume"}
                </button>
                <button
                  className="btn secondary"
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(s.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
