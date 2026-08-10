import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Sidebar } from "./components/common/Sidebar";
import { useTrayQueueControls } from "./hooks/useTrayQueueControls";
import { useUiStore } from "./store/ui";
import { Splash } from "./pages/Splash";
import { Dashboard } from "./pages/Dashboard";
import { Wizard } from "./pages/Wizard";
import { Generate } from "./pages/Generate";
import { History } from "./pages/History";
import { Influencers } from "./pages/Influencers";
import { InfluencerDetail } from "./pages/InfluencerDetail";
import { Wardrobe } from "./pages/Wardrobe";
import { Scheduler } from "./pages/Scheduler";
import { Settings } from "./pages/Settings";
import { EditPosts } from "./pages/EditPosts";

function Shell({ children }: { children: ReactNode }) {
  useTrayQueueControls();
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
              <Route path="/influencers" element={<Influencers />} />
              <Route path="/influencers/:id" element={<InfluencerDetail />} />
              <Route path="/wizard" element={<Wizard />} />
              <Route path="/generate" element={<Generate />} />
              <Route path="/history" element={<History />} />
              <Route path="/wardrobe" element={<Wardrobe />} />
              <Route path="/scheduler" element={<Scheduler />} />
              <Route path="/vault" element={<Navigate to="/" replace />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/monitor" element={<Navigate to="/settings" replace />} />
              <Route path="/post" element={<EditPosts />} />
              <Route path="/edit-posts" element={<EditPosts />} />
            </Routes>
          </Shell>
        }
      />
    </Routes>
  );
}
