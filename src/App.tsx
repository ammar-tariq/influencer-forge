import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Sidebar } from "./components/common/Sidebar";
import { useUiStore } from "./store/ui";
import { Splash } from "./pages/Splash";
import { Dashboard } from "./pages/Dashboard";
import { Wizard } from "./pages/Wizard";
import { Generate } from "./pages/Generate";
import { History } from "./pages/History";
import { Wardrobe } from "./pages/Wardrobe";
import { Scheduler } from "./pages/Scheduler";
import { Vault } from "./pages/Vault";
import { Settings } from "./pages/Settings";
import { Monitor } from "./pages/Monitor";
import { Post } from "./pages/Post";

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="p-6 md:p-8">{children}</main>
    </div>
  );
}

export default function App() {
  const ready = useUiStore((s) => s.ready);
  const location = useLocation();

  if (!ready && location.pathname !== "/splash") {
    return <Navigate to="/splash" replace />;
  }

  return (
    <Routes>
      <Route path="/splash" element={<Splash />} />
      <Route
        path="/*"
        element={
          <Shell>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/wizard" element={<Wizard />} />
              <Route path="/generate" element={<Generate />} />
              <Route path="/history" element={<History />} />
              <Route path="/wardrobe" element={<Wardrobe />} />
              <Route path="/scheduler" element={<Scheduler />} />
              <Route path="/vault" element={<Vault />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/monitor" element={<Monitor />} />
              <Route path="/post" element={<Post />} />
            </Routes>
          </Shell>
        }
      />
    </Routes>
  );
}
