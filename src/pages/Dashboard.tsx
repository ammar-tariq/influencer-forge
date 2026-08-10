import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ReadinessChecklist } from "../components/common/ReadinessChecklist";

export function Dashboard() {
  const influencers = useQuery({ queryKey: ["influencers"], queryFn: api.listInfluencers });
  const suggestions = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api.suggestions("Lifestyle"),
  });
  const reminders = useQuery({
    queryKey: ["reminders"],
    queryFn: api.reminders,
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl tracking-tight">Studio</h1>
        <p className="muted mt-1">
          CRUD is ready now. Real AI images start when the checklist below is green.
        </p>
      </header>

      <ReadinessChecklist />

      {!influencers.data?.length ? (
        <div className="panel">
          <h2 className="text-xl">Create your first influencer</h2>
          <p className="muted mt-2">Personality + Looks in a short wizard. No cloud account required.</p>
          <Link className="btn mt-4 inline-block" to="/wizard">
            Open wizard
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {influencers.data.map((inf) => (
            <div key={inf.id} className="panel">
              <h3 className="text-xl">{inf.name}</h3>
              <p className="muted text-sm">Influencer #{inf.id}</p>
              <Link className="btn mt-4 inline-block" to="/generate">
                Generate
              </Link>
            </div>
          ))}
        </div>
      )}

      <div className="panel">
        <h2 className="text-lg">Smart daily suggestions</h2>
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
            {reminders.data?.reminders.length} due — head to Generate when ready.
          </p>
        </div>
      )}
    </div>
  );
}
