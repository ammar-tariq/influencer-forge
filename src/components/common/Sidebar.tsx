import { NavLink } from "react-router-dom";
import { QueueStatusChip } from "./QueueStatus";
import { VaultToggle } from "./VaultToggle";
import {
  IconCalendar,
  IconHome,
  IconLibrary,
  IconSettings,
  IconShirt,
  IconUsers,
} from "./icons";

const links = [
  ["/", "Studio home", IconHome],
  ["/influencers", "Influencers", IconUsers],
  ["/history", "Library", IconLibrary],
  ["/wardrobe", "Wardrobe", IconShirt],
  ["/scheduler", "Scheduler", IconCalendar],
  ["/settings", "Settings", IconSettings],
] as const;

export function Sidebar() {
  return (
    <aside className="app-sidebar border-r border-[var(--line)] bg-[color-mix(in_srgb,var(--bg1)_92%,transparent)] p-5">
      <div className="mb-8">
        <div className="text-2xl tracking-tight">InfluencerForge</div>
        <p className="muted mt-1 text-sm">Local AI influencer studio</p>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {links.map(([to, label, Icon]) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `nav-link rounded-xl px-3 py-2 text-sm transition ${
                isActive ? "bg-[var(--bg2)] text-[var(--accent)]" : "text-[var(--muted)] hover:text-[var(--ink)]"
              }`
            }
          >
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <VaultToggle />
        <QueueStatusChip />
      </div>
    </aside>
  );
}
