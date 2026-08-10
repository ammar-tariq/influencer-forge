import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { MediaImage } from "../components/common/MediaImage";
import { ReadinessChecklist } from "../components/common/ReadinessChecklist";
import { FaceLockBadge } from "../components/common/StatusBadge";
import { IconCheck, IconClock } from "../components/common/icons";
import { useVault } from "../hooks/useVault";

export function Dashboard() {
  const influencers = useQuery({
    queryKey: ["influencers"],
    queryFn: api.listInfluencers,
    refetchInterval: 3000,
  });
  const generations = useQuery({
    queryKey: ["generations-dash"],
    queryFn: () => api.listGenerations(),
    refetchInterval: 4000,
  });
  const suggestions = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api.suggestions("Lifestyle"),
  });
  const reminders = useQuery({
    queryKey: ["reminders"],
    queryFn: api.reminders,
    refetchInterval: 10000,
  });
  const { status: vault } = useVault();
  const readiness = useQuery({ queryKey: ["readiness"], queryFn: api.readiness, refetchInterval: 8000 });

  const hasInfluencers = (influencers.data?.length ?? 0) > 0;
  const hasGens = (generations.data?.length ?? 0) > 0;
  const pending = generations.data?.filter((g) =>
    ["pending", "queued", "processing"].includes(g.status),
  ).length;
  const nsfwPendingVault = vault.data?.pending_nsfw ?? 0;

  const nextSteps = [
    {
      done: hasInfluencers,
      title: "1. Create an influencer",
      detail: "Personality → Face → Body (gender, height, curves, etc.)",
      to: "/wizard",
      cta: "Open Create",
    },
    {
      done: hasInfluencers,
      title: "2. Browse your influencers",
      detail: "See everyone, open a profile, and jump into their posts",
      to: "/influencers",
      cta: "Influencers",
    },
    {
      done: hasGens,
      title: "3. Generate a full-body post",
      detail: "Pick framing, pose, and outfit — prompts are optional extras",
      to: "/generate",
      cta: "Open Generate",
    },
    {
      done: Boolean(vault.data?.configured),
      title: "4. Set a Privacy Vault PIN",
      detail: "Encrypts NSFW outputs automatically when unlocked",
      to: "/vault",
      cta: "Open Vault",
    },
    {
      done: readiness.data?.mode === "real",
      title: "5. Real AI mode green",
      detail: readiness.data?.summary ?? "Finish the readiness checklist for ComfyUI",
      to: "/settings",
      cta: "Settings",
    },
  ];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Studio</h1>
        <p className="muted mt-1">
          Follow the checklist — each step links you to the right screen.
          {pending ? ` · ${pending} generation(s) in progress` : ""}
        </p>
      </header>

      <div className="panel">
        <h2 className="text-lg">What to do next</h2>
        <ul className="mt-4 space-y-3">
          {nextSteps.map((s) => (
            <li
              key={s.title}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[var(--bg2)] px-4 py-3"
            >
              <div className="flex min-w-0 items-start gap-3">
                <span className={`status-badge ${s.done ? "tone-ok" : "tone-wait"}`} title={s.done ? "Done" : "Todo"}>
                  {s.done ? <IconCheck size={13} /> : <IconClock size={13} />}
                </span>
                <div className="min-w-0">
                  <div className="font-semibold">{s.title.replace(/^\d+\.\s*/, "")}</div>
                  <p className="muted text-sm">{s.detail}</p>
                </div>
              </div>
              {!s.done && (
                <Link className="btn secondary" to={s.to}>
                  {s.cta}
                </Link>
              )}
              {s.done && (
                <Link className="btn secondary" to={s.to}>
                  Open
                </Link>
              )}
            </li>
          ))}
        </ul>
        {nsfwPendingVault > 0 && (
          <p className="mt-4 text-sm text-[var(--accent-2)]">
            {nsfwPendingVault} NSFW file(s) still in cleartext —{" "}
            <Link className="underline" to="/vault">
              unlock vault & secure them
            </Link>
            .
          </p>
        )}
      </div>

      <ReadinessChecklist />

      {!hasInfluencers ? (
        <div className="panel">
          <h2 className="text-xl">Create your first influencer</h2>
          <p className="muted mt-2">
            You’ll set personality, face, and body, then open their profile to create posts and
            browse everything they’ve made.
          </p>
          <Link className="btn mt-4 inline-block" to="/wizard">
            Start Create wizard
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {influencers.data!.map((inf) => (
            <div key={inf.id} className="panel overflow-hidden">
              <MediaImage
                path={inf.avatar_path}
                alt={inf.name}
                className="mb-3 h-56 w-full rounded-xl object-cover"
                fallback="Portrait generating…"
              />
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-xl">{inf.name}</h3>
                <FaceLockBadge faceLock={inf.face_lock} />
              </div>
              <p className="muted mt-1 text-sm">
                #{inf.id}
                {inf.age_rating ? ` · ${inf.age_rating}` : ""}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link className="btn inline-block" to={`/influencers/${inf.id}`}>
                  Open profile
                </Link>
                <Link className="btn secondary inline-block" to="/generate" state={{ createdId: inf.id, name: inf.name }}>
                  Create post
                </Link>
                <Link className="btn secondary inline-block" to={`/history?influencer=${inf.id}`}>
                  Their posts
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="panel">
        <h2 className="text-lg">Ideas</h2>
        <ul className="muted mt-3 list-disc space-y-1 pl-5 text-sm">
          {(suggestions.data?.suggestions ?? []).map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </div>

      {(reminders.data?.reminders?.length ?? 0) > 0 && (
        <div className="panel border-[var(--accent-2)]">
          <h2 className="text-lg">Schedule reminders</h2>
          <p className="muted mt-2 text-sm">
            {reminders.data?.reminders.length} due —{" "}
            <Link className="underline" to="/generate">
              Generate now
            </Link>
            .
          </p>
        </div>
      )}
    </div>
  );
}
