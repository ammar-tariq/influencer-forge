import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

export function ReadinessChecklist() {
  const readiness = useQuery({
    queryKey: ["readiness"],
    queryFn: api.readiness,
    refetchInterval: 5000,
  });
  const data = readiness.data;
  if (!data) {
    return <div className="panel muted text-sm">Checking studio readiness…</div>;
  }

  return (
    <div className="panel">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-lg">Generation readiness</h2>
          <p className="muted mt-1 text-sm">{data.summary}</p>
        </div>
        <div
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            data.real_ready
              ? "bg-[color-mix(in_srgb,var(--accent)_25%,transparent)] text-[var(--accent)]"
              : "bg-[color-mix(in_srgb,var(--accent-2)_25%,transparent)] text-[var(--accent-2)]"
          }`}
        >
          mode: {data.mode}
        </div>
      </div>
      <ul className="mt-4 space-y-2 text-sm">
        {data.checklist.map((item) => (
          <li key={item.id} className="flex gap-3">
            <span className={item.ok ? "text-[var(--accent)]" : "text-[var(--danger)]"}>
              {item.ok ? "OK" : "··"}
            </span>
            <div>
              <div>{item.label}</div>
              {!item.ok && <p className="muted mt-0.5 text-xs">{item.fix}</p>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
