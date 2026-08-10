import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { MediaImage } from "../components/common/MediaImage";

export function Influencers() {
  const influencers = useQuery({
    queryKey: ["influencers"],
    queryFn: api.listInfluencers,
    refetchInterval: 4000,
  });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl tracking-tight">Influencers</h1>
          <p className="muted mt-1">All of your creators — open one for details and their posts.</p>
        </div>
        <Link className="btn" to="/wizard">
          New influencer
        </Link>
      </header>

      {!influencers.data?.length ? (
        <div className="panel">
          <h2 className="text-xl">No influencers yet</h2>
          <p className="muted mt-2">Create personality, face, and body in a short wizard.</p>
          <Link className="btn mt-4 inline-block" to="/wizard">
            Start Create wizard
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {influencers.data.map((inf) => (
            <Link key={inf.id} to={`/influencers/${inf.id}`} className="panel block text-left transition hover:border-[var(--accent)]">
              <MediaImage
                path={inf.avatar_path}
                alt={inf.name}
                className="mb-3 h-48 w-full rounded-xl object-cover"
                fallback="No photo yet"
              />
              <h2 className="text-xl">{inf.name}</h2>
              <p className="muted mt-1 text-sm">
                {inf.niche ?? "Creator"}
                {inf.age_rating ? ` · ${inf.age_rating}` : ""}
              </p>
              <p className="muted mt-1 text-sm">
                {inf.generation_count ?? 0} post{(inf.generation_count ?? 0) === 1 ? "" : "s"}
                {inf.face_lock && inf.face_lock !== "none"
                  ? ` · face lock: ${inf.face_lock.replace("_", " ")}`
                  : ""}
              </p>
              <span className="mt-3 inline-block text-sm text-[var(--accent)]">View details →</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
