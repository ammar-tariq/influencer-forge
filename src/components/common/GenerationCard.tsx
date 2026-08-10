import type { Generation } from "../../types";
import { MediaImage } from "./MediaImage";
import { StatusBadge } from "./StatusBadge";

type Props = {
  generation: Generation;
  imagePath?: string | null;
  onClick: () => void;
};

export function GenerationCard({ generation: g, imagePath, onClick }: Props) {
  const isVideo =
    g.workflow_type === "video" || Boolean(g.output_path?.match(/\.(mp4|webm|mov)$/i));
  const path =
    imagePath ??
    (g.is_vaulted
      ? g.teaser_path
      : (g.output_thumbnail_path ?? (isVideo ? null : g.output_path) ?? g.teaser_path));

  return (
    <button type="button" className="panel gen-card text-left" onClick={onClick}>
      <div className="gen-card-media">
        <MediaImage
          path={path}
          alt=""
          className="h-40 w-full rounded-xl object-cover"
          fallback={g.status === "completed" ? (isVideo ? "Video" : "No preview") : g.status}
          cacheKey={g.completed_at ?? g.seed ?? g.id}
        />
        <StatusBadge
          status={g.status}
          isVaulted={g.is_vaulted}
          isNsfw={g.is_nsfw}
          overlay
        />
        {isVideo && (
          <span className="status-badge tone-busy" style={{ position: "absolute", left: "0.55rem", top: "0.55rem" }}>
            Video
          </span>
        )}
      </div>
      <p className="gen-card-prompt">{g.user_prompt}</p>
      <span className="gen-card-id">#{g.id}</span>
    </button>
  );
}
