"""Studio readiness checks — what is needed before real generation works."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge_python.comfyui_client import ComfyUIClient
from forge_python.config import settings
from forge_python.lip_sync import ffmpeg_available

CHECKPOINT_GLOBS = ("*.safetensors", "*.ckpt", "*.pt")


def _is_likely_checkpoint(path: Path) -> bool:
    """Filter out Diffusers shard files; keep single-file SDXL/SD checkpoints."""
    name = path.name.lower()
    if name.startswith(".") or name == "put_checkpoints_here":
        return False
    # Ignore common non-checkpoint safetensors from Diffusers trees
    if any(part in {"vae", "text_encoder", "transformer", "unconditional_transformer"} for part in path.parts):
        return False
    try:
        # Full SDXL fp16 checkpoints are multi-GB; skip tiny marker files
        if path.stat().st_size < 100_000_000:
            return False
    except OSError:
        return False
    return True


def find_checkpoints() -> list[Path]:
    roots = [
        settings.comfyui_root / "models" / "checkpoints",
        settings.models_dir / "checkpoints",
        settings.models_dir,
        *settings.extra_model_dirs,
    ]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in CHECKPOINT_GLOBS:
            found.extend(sorted(root.glob(pattern)))
            found.extend(sorted(root.glob(f"**/{pattern}")))
    # de-dupe preserving order; prefer ComfyUI checkpoints dir first
    seen: set[str] = set()
    unique: list[Path] = []
    for path in found:
        if not _is_likely_checkpoint(path):
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def workflow_ready(name: str = "image_faceid.json") -> bool:
    path = settings.workflows_dir / name
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(data.get("prompt"))


def find_named_model(filename: str, *subdirs: str) -> Path | None:
    roots = [
        settings.comfyui_root / "models",
        settings.models_dir,
        *settings.extra_model_dirs,
    ]
    for root in roots:
        if not root.exists():
            continue
        direct = root.joinpath(*subdirs, filename) if subdirs else root / filename
        if direct.is_file():
            return direct
        matches = list(root.rglob(filename))
        if matches:
            return matches[0]
    return None


def ipadapter_custom_node_installed() -> bool:
    root = settings.comfyui_root / "custom_nodes"
    if not root.is_dir():
        return False
    for name in ("ComfyUI_IPAdapter_plus", "comfyui_ipadapter_plus", "IPAdapter"):
        if (root / name).is_dir():
            return True
    return False


def faceid_weights_present() -> dict[str, Any]:
    ipa = find_named_model("ip-adapter-faceid-plusv2_sdxl.bin", "ipadapter")
    if ipa is None:
        ipa = find_named_model("ip-adapter-faceid-plusv2_sdxl.bin")
    clip = find_named_model("CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors", "clip_vision")
    if clip is None:
        clip = find_named_model("CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors")
    return {
        "ok": bool(ipa and clip),
        "ipadapter": str(ipa) if ipa else None,
        "clip_vision": str(clip) if clip else None,
        "ipadapter_file": ipa.name if ipa else "ip-adapter-faceid-plusv2_sdxl.bin",
        "clip_vision_file": clip.name if clip else "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
    }


def animatediff_custom_node_installed() -> bool:
    root = settings.comfyui_root / "custom_nodes"
    if not root.is_dir():
        return False
    for name in (
        "ComfyUI-AnimateDiff-Evolved",
        "comfyui-animatediff",
        "AnimateDiff",
    ):
        if (root / name).is_dir():
            return True
    return False


def find_motion_module() -> Path | None:
    roots = [
        settings.comfyui_root / "models" / "animatediff_models",
        settings.comfyui_root / "custom_nodes" / "ComfyUI-AnimateDiff-Evolved" / "models",
        settings.models_dir,
    ]
    patterns = ("*mm_sdxl*", "*v3_sd15*", "*mm_sd_v15*")
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            found = sorted(root.glob(pattern)) + sorted(root.glob(f"**/{pattern}"))
            for path in found:
                if path.is_file() and path.stat().st_size > 10_000_000:
                    return path
    return None


async def collect_readiness(comfy: ComfyUIClient | None = None) -> dict[str, Any]:
    client = comfy or ComfyUIClient()
    comfy_installed = (settings.comfyui_root / "main.py").exists()
    checkpoints = find_checkpoints()
    healthy = await client.health() if settings.enable_comfyui or comfy_installed else False
    wf_ok = workflow_ready("image_faceid.json")
    img2img_ok = workflow_ready("image_img2img.json")
    faceid_wf = workflow_ready("image_ipadapter_faceid.json")
    faceid_node = ipadapter_custom_node_installed()
    faceid_w = faceid_weights_present()
    video_wf = workflow_ready("video_animate.json")
    ad_node = animatediff_custom_node_installed()
    motion = find_motion_module()
    node_types: set[str] = set()
    if healthy:
        node_types = await client.object_info_class_types()
    faceid_nodes_live = {"IPAdapterFaceID", "IPAdapterModelLoader"}.issubset(node_types) if node_types else False
    checklist = [
        {
            "id": "comfyui_source",
            "label": "ComfyUI source present",
            "ok": comfy_installed,
            "detail": str(settings.comfyui_root / "main.py"),
            "fix": "Clone ComfyUI into src-tauri/resources/comfyui/ComfyUI (see README there).",
        },
        {
            "id": "comfyui_enabled",
            "label": "IFORGE_ENABLE_COMFYUI=1",
            "ok": settings.enable_comfyui,
            "detail": "enabled" if settings.enable_comfyui else "disabled",
            "fix": "export IFORGE_ENABLE_COMFYUI=1 before starting the orchestrator.",
        },
        {
            "id": "checkpoint",
            "label": "SDXL / diffusion checkpoint on disk",
            "ok": len(checkpoints) > 0,
            "detail": str(checkpoints[0]) if checkpoints else "none found",
            "fix": (
                "Place a single-file SDXL .safetensors under "
                f"{settings.comfyui_root / 'models' / 'checkpoints'} "
                "or point IFORGE_EXTRA_MODEL_DIRS at your model folder "
                "(e.g. /Volumes/external/hfModels)."
            ),
        },
        {
            "id": "workflow",
            "label": "Image workflow graph ready",
            "ok": wf_ok,
            "detail": str(settings.workflows_dir / "image_faceid.json"),
            "fix": "Ensure workflow JSON includes a ComfyUI prompt graph.",
        },
        {
            "id": "workflow_img2img",
            "label": "Face-lock img2img workflow ready",
            "ok": img2img_ok,
            "detail": str(settings.workflows_dir / "image_img2img.json"),
            "fix": "Ship image_img2img.json under src-tauri/resources/workflows/.",
        },
        {
            "id": "comfyui_healthy",
            "label": "ComfyUI HTTP healthy (:8188)",
            "ok": healthy,
            "detail": settings.comfyui_url,
            "fix": "Start ComfyUI or let the app spawn it once source + enable flag are set.",
        },
        {
            "id": "ipadapter_faceid",
            "label": "IP-Adapter FaceID Plus (optional, stronger identity)",
            "ok": faceid_wf and faceid_node and faceid_w["ok"],
            "detail": (
                f"nodes={'live' if faceid_nodes_live else ('installed' if faceid_node else 'missing')}; "
                f"ipa={faceid_w['ipadapter'] or 'missing'}; clip={faceid_w['clip_vision'] or 'missing'}"
            ),
            "fix": (
                "Install ComfyUI_IPAdapter_plus under custom_nodes/ and place "
                "ip-adapter-faceid-plusv2_sdxl.bin + CLIP-ViT-H-14… under models/ "
                "(see src-tauri/resources/comfyui/README.md). Falls back to img2img."
            ),
        },
        {
            "id": "animatediff",
            "label": "AnimateDiff video (optional)",
            "ok": video_wf and ad_node and motion is not None,
            "detail": (
                f"node={'yes' if ad_node else 'no'}; "
                f"motion={motion.name if motion else 'missing'}"
            ),
            "fix": (
                "Install ComfyUI-AnimateDiff-Evolved + an SDXL/SD1.5 motion module "
                "(see comfyui README). Video falls back to stub/still until ready."
            ),
        },
        {
            "id": "talking_head",
            "label": "Talking-head / lip-sync (ffmpeg)",
            "ok": ffmpeg_available(),
            "detail": "ffmpeg on PATH → face still + audio mux (ComfyUI-Wav2Lip later)",
            "fix": "Install ffmpeg (e.g. brew install ffmpeg). Needs Face Seed + audio upload.",
        },
    ]
    # Core path for "real" mode — FaceID/AnimateDiff remain optional enhancements.
    core_ids = {
        "comfyui_source",
        "comfyui_enabled",
        "checkpoint",
        "workflow",
        "workflow_img2img",
        "comfyui_healthy",
    }
    real_ready = all(item["ok"] for item in checklist if item["id"] in core_ids)
    mode = "real" if real_ready else "stub"
    return {
        "mode": mode,
        "real_ready": real_ready,
        "allow_stub_fallback": settings.allow_stub_fallback,
        "enable_comfyui": settings.enable_comfyui,
        "comfyui_installed": comfy_installed,
        "comfyui_healthy": healthy,
        "checkpoint_count": len(checkpoints),
        "checkpoints": [str(p) for p in checkpoints[:10]],
        "workflow_ready": wf_ok,
        "faceid_ready": faceid_wf and faceid_node and faceid_w["ok"],
        "faceid_weights": faceid_w,
        "animatediff_ready": video_wf and ad_node and motion is not None,
        "checklist": checklist,
        "summary": (
            "Real generation ready."
            if real_ready
            else "Stub mode — CRUD + placeholder images until ComfyUI + checkpoint are ready."
        ),
    }
