import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { MediaImage } from "../components/common/MediaImage";
import { ReadinessChecklist } from "../components/common/ReadinessChecklist";
import { IconCheck } from "../components/common/icons";

export function Dashboard() {
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const suggestions = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api.suggestions("Lifestyle"),
  });
  const reminders = useQuery({ queryKey: ["reminders"], queryFn: api.reminders });
  const vaultStatus = useQuery({ queryKey: ["vault-status"], queryFn: api.vaultStatus });
  const readiness = useQuery({ queryKey: ["readiness"], queryFn: api.readiness, refetchInterval: 8000 });

  const hasInfluencers = Boolean(influencers.data?.length);
  const realReady = Boolean(readiness.data?.real_ready);
  const nsfwPendingVault = vaultStatus.data?.pending_nsfw ?? 0;

  const steps = [
    {
      title: "1. Create an influencer",
      detail: "Personality, face, body",
      to: "/wizard",
      cta: "Create",
      done: hasInfluencers,
    },
    {
      title: "2. Browse profiles",
      detail: "Edit looks, wardrobe, posts",
      to: "/influencers",
      cta: "Open",
      done: hasInfluencers,
    },
    {
      title: "3. Create a post",
      detail: "Scene + optional wardrobe outfit",
      to: "/generate",
      cta: "Generate",
      done: false,
    },
    {
      title: "4. Wardrobe",
      detail: "Reusable outfits (bikini, hoodie…)",
      to: "/wardrobe",
      cta: "Outfits",
      done: false,
    },
  ];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Studio home</h1>
        <p className="muted mt-1">
          Local influencer studio
          {realReady ? " · real generation ready" : " · stub / setup mode"}
        </p>
      </header>

      <div className="panel">
        <h2 className="text-lg">Get started</h2>
        <ul className="mt-4 space-y-3">
          {steps.map((s) => (
            <li key={s.title} className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-start gap-3 min-w-0">
                {s.done ? (
                  <IconCheck size={18} className="mt-0.5 text-[var(--accent)]" />
                ) : (
                  <span className="mt-0.5 inline-block h-[18px] w-[18px] rounded-full border border-[var(--line)]" />
                )}
                <div className="min-w-0">
                  <div className="font-semibold">{s.title.replace(/^\d+\.\s*/, "")}</div>
                  <p className="muted text-sm">{s.detail}</p>
                </div>
              </div>
              <Link className="btn secondary" to={s.to}>
                {s.done ? "Open" : s.cta}
              </Link>
            </li>
          ))}
        </ul>
        {nsfwPendingVault > 0 && (
          <p className="mt-4 text-sm text-[var(--accent-2)]">
            {nsfwPendingVault} NSFW file(s) waiting to encrypt — turn on{" "}
            <strong>Privacy vault</strong> in the sidebar (PIN) and they auto-vault.
          </p>
        )}
      </div>

      <ReadinessChecklist />

      {!hasInfluencers ? (
        <div className="panel">
          <h2 className="text-xl">Create your first influencer</h2>
          <p className="muted mt-2">
            You’ll set personality, face, and body, then open their profile to create posts.
          </p>
          <Link className="btn mt-4 inline-block" to="/wizard">
            Start Create wizard
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {influencers.data!.map((inf) => (
            <Link
              key={inf.id}
              to={`/influencers/${inf.id}`}
              className="panel block overflow-hidden text-left transition hover:border-[var(--accent)]"
            >
              <MediaImage
                path={inf.avatar_path}
                alt={inf.name}
                className="mb-3 h-56 w-full rounded-xl object-cover media-face"
                fallback="Portrait generating…"
              />
              <h3 className="text-xl">{inf.name}</h3>
              <p className="muted mt-1 text-sm">
                #{inf.id}
                {inf.age_rating ? ` · ${inf.age_rating}` : ""}
                {` · ${inf.generation_count ?? 0} posts`}
              </p>
            </Link>
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
