"""Talking-head video: Wav2Lip (ComfyUI) when installed, else ffmpeg face+audio mux."""

from __future__ import annotations

import asyncio
import logging
import random
import shutil
import subprocess
import uuid
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


def wav2lip_node_installed() -> bool:
    root = settings.comfyui_root / "custom_nodes"
    return (root / "ComfyUI_wav2lip").is_dir() or any(
        p.is_dir() and "wav2lip" in p.name.lower() for p in root.glob("*") if p.is_dir()
    )


def wav2lip_checkpoint_present() -> Path | None:
    root = settings.comfyui_root / "custom_nodes"
    for node in root.glob("*wav2lip*"):
        for cand in (
            node / "checkpoints" / "wav2lip_gan.pth",
            node / "Wav2Lip" / "checkpoints" / "wav2lip_gan.pth",
        ):
            if cand.is_file() and cand.stat().st_size > 1_000_000:
                return cand
    return None


def wav2lip_ready() -> bool:
    return wav2lip_node_installed() and wav2lip_checkpoint_present() is not None


def resolve_audio_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = settings.data_dir / path
    if path.is_file() and path.suffix.lower() in _AUDIO_SUFFIXES:
        return path.resolve()
    alt = settings.uploads_dir / Path(raw).name
    if alt.is_file() and alt.suffix.lower() in _AUDIO_SUFFIXES:
        return alt.resolve()
    return None


async def _generate_via_wav2lip_comfy(
    *,
    generation_id: int,
    face_image: Path,
    audio_path: Path,
    width: int,
    height: int,
    used_seed: int,
) -> tuple[Path, Path, int, str]:
    """Run LoadImage → LoadAudio → Wav2Lip → VHS_VideoCombine via ComfyUI API."""
    from forge_python.comfyui_client import ComfyUIClient

    client = ComfyUIClient()
    if not await client.health():
        client.start_process()
        for _ in range(30):
            if await client.health():
                break
            await asyncio.sleep(0.5)
    if not await client.health():
        raise RuntimeError("ComfyUI not healthy for Wav2Lip")

    info = await client.object_info()
    if "Wav2Lip" not in info:
        raise RuntimeError("Wav2Lip node not loaded — restart ComfyUI after install-wav2lip.sh")

    input_dir = settings.comfyui_root / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    tag = f"iforge_{generation_id}_{uuid.uuid4().hex[:8]}"
    face_name = f"{tag}_face.png"
    audio_name = f"{tag}_audio{audio_path.suffix.lower()}"
    face_dest = input_dir / face_name
    audio_dest = input_dir / audio_name

    with Image.open(face_image) as im:
        rgb = im.convert("RGB")
        rgb = rgb.resize((width, height), Image.Resampling.LANCZOS)
        rgb.save(face_dest)
    shutil.copy2(audio_path, audio_dest)

    load_audio_cls = "LoadAudio" if "LoadAudio" in info else None
    if load_audio_cls is None:
        raise RuntimeError("LoadAudio node missing (bundled with ComfyUI_wav2lip)")

    prompt: dict = {
        "1": {"class_type": "LoadImage", "inputs": {"image": face_name}},
        "2": {"class_type": load_audio_cls, "inputs": {"audio": audio_name}},
        "3": {
            "class_type": "Wav2Lip",
            "inputs": {
                "images": ["1", 0],
                "audio": ["2", 0],
                "mode": "repetitive",
                "face_detect_batch": 8,
            },
        },
        "4": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["3", 0],
                "frame_rate": 25,
                "loop_count": 0,
                "filename_prefix": f"iforge_lipsync_{generation_id}",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }
    # Prefer wiring Wav2Lip audio into VHS when the node accepts it.
    vhs_inputs = (info.get("VHS_VideoCombine") or {}).get("input", {}).get("required", {})
    if "audio" in vhs_inputs or "audio" in (info.get("VHS_VideoCombine") or {}).get("input", {}).get(
        "optional", {}
    ):
        prompt["4"]["inputs"]["audio"] = ["3", 1]

    prompt_id = await client.queue_prompt(prompt)
    media = await client.wait_for_media(prompt_id, timeout_s=600.0)
    video = next((m for m in media if m.get("kind") == "video"), None)
    image = next((m for m in media if m.get("kind") == "image"), None)
    if not video:
        raise RuntimeError("Wav2Lip produced no video output — check ComfyUI logs / ffmpeg")

    settings.ensure_directories()
    out = settings.generations_dir / f"{generation_id}.mp4"
    thumb = settings.thumbnails_dir / f"{generation_id}_thumb.png"
    await client.download_image(video, out)
    if image:
        frame = settings.generations_dir / f"{generation_id}_w2l_frame.png"
        await client.download_image(image, frame)
        with Image.open(frame) as im:
            im.convert("RGB").thumbnail((256, 256))
            im.convert("RGB").save(thumb)
        frame.unlink(missing_ok=True)
    else:
        with Image.open(face_dest) as im:
            im.convert("RGB").thumbnail((256, 256))
            im.convert("RGB").save(thumb)

    for p in (face_dest, audio_dest):
        try:
            p.unlink()
        except OSError:
            pass
    return out, thumb, used_seed, "wav2lip"


async def _generate_via_ffmpeg(
    *,
    generation_id: int,
    face_image: Path,
    audio_path: Path,
    aspect_ratio: str,
    used_seed: int,
) -> tuple[Path, Path, int, str]:
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg not found on PATH — install ffmpeg for talking-head / lip-sync videos"
        )
    width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])
    settings.ensure_directories()
    out = settings.generations_dir / f"{generation_id}.mp4"
    thumb = settings.thumbnails_dir / f"{generation_id}_thumb.png"
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


async def generate_talking_head(
    *,
    generation_id: int,
    face_image: Path,
    audio_path: Path,
    aspect_ratio: str = "9:16",
    seed: int | None = None,
) -> tuple[Path, Path, int, str]:
    """Return (mp4_path, thumb_path, seed, model_used). Prefers Wav2Lip when ready."""
    if not face_image.is_file():
        raise RuntimeError("Talking-head needs a face image (Face Seed or base portrait)")
    if not audio_path.is_file():
        raise RuntimeError("Talking-head audio file missing")

    used_seed = seed if seed is not None else random.randint(1, 2_147_483_647)
    width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])

    if wav2lip_ready() and settings.enable_comfyui:
        try:
            return await _generate_via_wav2lip_comfy(
                generation_id=generation_id,
                face_image=face_image,
                audio_path=audio_path,
                width=width,
                height=height,
                used_seed=used_seed,
            )
        except Exception as exc:
            logger.warning("Wav2Lip failed (%s) — falling back to ffmpeg still+audio", exc)

    return await _generate_via_ffmpeg(
        generation_id=generation_id,
        face_image=face_image,
        audio_path=audio_path,
        aspect_ratio=aspect_ratio,
        used_seed=used_seed,
    )
