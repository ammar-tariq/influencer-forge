import { NavLink } from "react-router-dom";
import { QueueStatusChip } from "./QueueStatus";

const links = [
  ["/", "Studio home"],
  ["/influencers", "Influencers"],
  ["/wizard", "New influencer"],
  ["/generate", "Create post"],
  ["/history", "Library"],
  ["/wardrobe", "Wardrobe"],
  ["/scheduler", "Scheduler"],
  ["/vault", "Privacy Vault"],
  ["/settings", "Settings"],
  ["/monitor", "System"],
  ["/post", "Edit photo"],
] as const;

export function Sidebar() {
  return (
    <aside className="border-r border-[var(--line)] bg-[color-mix(in_srgb,var(--bg1)_92%,transparent)] p-5">
      <div className="mb-8">
        <div className="text-2xl tracking-tight">InfluencerForge</div>
        <p className="muted mt-1 text-sm">Local AI influencer studio</p>
      </div>
      <nav className="flex flex-col gap-1">
        {links.map(([to, label]) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `rounded-xl px-3 py-2 text-sm transition ${
                isActive ? "bg-[var(--bg2)] text-[var(--accent)]" : "text-[var(--muted)] hover:text-[var(--ink)]"
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-8">
        <QueueStatusChip />
      </div>
    </aside>
  );
}
