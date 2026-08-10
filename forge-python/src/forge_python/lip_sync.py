"""Talking-head video: mux a face still with audio (ffmpeg).

ComfyUI-Wav2Lip is not bundled yet — this produces a real playable .mp4 with the
influencer face locked to the uploaded audio duration. When a Wav2Lip custom node
is installed later, comfyui_client can take over the same workflow_type.
"""

from __future__ import annotations

import asyncio
import logging
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from forge_python.config import settings

logger = logging.getLogger(__name__)

ASPECT_SIZES = {
    "9:16": (576, 1024),
    "16:9": (1024, 576),
    "1:1": (768, 768),
}

_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def resolve_audio_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = settings.data_dir / path
    if path.is_file() and path.suffix.lower() in _AUDIO_SUFFIXES:
        return path.resolve()
    # Also allow under media/uploads
    alt = settings.uploads_dir / Path(raw).name
    if alt.is_file() and alt.suffix.lower() in _AUDIO_SUFFIXES:
        return alt.resolve()
    return None


async def generate_talking_head(
    *,
    generation_id: int,
    face_image: Path,
    audio_path: Path,
    aspect_ratio: str = "9:16",
    seed: int | None = None,
) -> tuple[Path, Path, int, str]:
    """Return (mp4_path, thumb_path, seed, model_used)."""
    if not face_image.is_file():
        raise RuntimeError("Talking-head needs a face image (Face Seed or base portrait)")
    if not audio_path.is_file():
        raise RuntimeError("Talking-head audio file missing")
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg not found on PATH — install ffmpeg for talking-head / lip-sync videos"
        )

    used_seed = seed if seed is not None else random.randint(1, 2_147_483_647)
    width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])
    settings.ensure_directories()
    out = settings.generations_dir / f"{generation_id}.mp4"
    thumb = settings.thumbnails_dir / f"{generation_id}_thumb.png"

    # Thumbnail from face still
    with Image.open(face_image) as im:
        rgb = im.convert("RGB")
        rgb.thumbnail((256, 256))
        rgb.save(thumb)

    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(face_image),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-vf",
        vf,
        "-movflags",
        "+faststart",
        str(out),
    ]
    logger.info("Talking-head ffmpeg for generation %s", generation_id)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()
    if proc.returncode != 0 or not out.is_file():
        err = (stderr or b"").decode("utf-8", errors="replace")[-800:]
        raise RuntimeError(f"ffmpeg talking-head failed: {err}")
    return out, thumb, used_seed, "talking_head_ffmpeg"
