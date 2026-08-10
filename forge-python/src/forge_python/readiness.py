"""Studio readiness checks — what is needed before real generation works."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge_python.comfyui_client import ComfyUIClient
from forge_python.config import settings

CHECKPOINT_GLOBS = ("*.safetensors", "*.ckpt", "*.pt")


def find_checkpoints() -> list[Path]:
    roots = [
        settings.comfyui_root / "models" / "checkpoints",
        settings.models_dir / "checkpoints",
        settings.models_dir,
    ]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in CHECKPOINT_GLOBS:
            found.extend(sorted(root.glob(pattern)))
            found.extend(sorted(root.glob(f"**/{pattern}")))
    # de-dupe preserving order
    seen: set[str] = set()
    unique: list[Path] = []
    for path in found:
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


async def collect_readiness(comfy: ComfyUIClient | None = None) -> dict[str, Any]:
    client = comfy or ComfyUIClient()
    comfy_installed = (settings.comfyui_root / "main.py").exists()
    checkpoints = find_checkpoints()
    healthy = await client.health() if settings.enable_comfyui or comfy_installed else False
    wf_ok = workflow_ready()
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
                "Place sd_xl_base_1.0.safetensors under "
                f"{settings.comfyui_root / 'models' / 'checkpoints'}"
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
            "id": "comfyui_healthy",
            "label": "ComfyUI HTTP healthy (:8188)",
            "ok": healthy,
            "detail": settings.comfyui_url,
            "fix": "Start ComfyUI or let the app spawn it once source + enable flag are set.",
        },
    ]
    real_ready = all(item["ok"] for item in checklist)
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
        "checklist": checklist,
        "summary": (
            "Real generation ready."
            if real_ready
            else "Stub mode — CRUD + placeholder images until ComfyUI + checkpoint are ready."
        ),
    }
