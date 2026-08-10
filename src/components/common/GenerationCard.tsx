import type { Generation } from "../../types";
import { MediaImage } from "./MediaImage";
import { StatusBadge } from "./StatusBadge";

type Props = {
  generation: Generation;
  imagePath?: string | null;
  onClick: () => void;
};

export function GenerationCard({ generation: g, imagePath, onClick }: Props) {
  const hasPlayableVideo = Boolean(g.output_path?.match(/\.(mp4|webm|mov)$/i));
  const videoJob = g.workflow_type === "video" || g.workflow_type === "lip_sync";
  const path =
    imagePath ??
    (g.is_vaulted
      ? g.teaser_path
      : (g.output_thumbnail_path ?? (hasPlayableVideo ? null : g.output_path) ?? g.teaser_path));

  return (
    <button type="button" className="panel gen-card text-left" onClick={onClick}>
      <div className="gen-card-media">
        <MediaImage
          path={path}
          alt=""
          className="h-40 w-full rounded-xl object-cover"
          fallback={
            g.status === "completed"
              ? videoJob && !hasPlayableVideo
                ? "Video failed"
                : hasPlayableVideo
                  ? "Video"
                  : "No preview"
              : g.status
          }
          cacheKey={g.completed_at ?? g.seed ?? g.id}
          faceFocus
        />
        <StatusBadge
          status={g.status}
          isVaulted={g.is_vaulted}
          isNsfw={g.is_nsfw}
          overlay
        />
        {videoJob && (
          <span className="status-badge tone-busy" style={{ position: "absolute", left: "0.55rem", top: "0.55rem" }}>
            {hasPlayableVideo ? "Video" : "Video (no mp4)"}
          </span>
        )}
      </div>
      <p className="gen-card-prompt">{g.user_prompt}</p>
      <span className="gen-card-id">#{g.id}</span>
    </button>
  );
}
