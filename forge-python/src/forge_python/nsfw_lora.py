"""Optional NSFW LoRA injection when a matching weight exists under models/loras/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from forge_python.config import settings


def find_nsfw_lora() -> Path | None:
    """Return first LoRA whose name suggests NSFW (not vendored in git)."""
    roots = [
        settings.comfyui_root / "models" / "loras",
        settings.models_dir / "loras",
        *settings.extra_model_dirs,
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".safetensors", ".pt", ".ckpt"}:
                continue
            name = path.name.lower()
            if any(tok in name for tok in ("nsfw", "nude", "explicit", "xxx")):
                candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def apply_nsfw_lora(prompt: dict[str, Any], *, strength: float = 0.75) -> str | None:
    """Insert LoraLoader after CheckpointLoaderSimple and rewire MODEL/CLIP.

    Returns the LoRA filename used, or None if nothing applied.
    """
    lora = find_nsfw_lora()
    if lora is None:
        return None
    ckpt_id: str | None = None
    for nid, node in prompt.items():
        if isinstance(node, dict) and node.get("class_type") == "CheckpointLoaderSimple":
            ckpt_id = str(nid)
            break
    if ckpt_id is None:
        return None

    lora_id = "90"
    while lora_id in prompt:
        lora_id = str(int(lora_id) + 1)

    prompt[lora_id] = {
        "class_type": "LoraLoader",
        "inputs": {
            "model": [ckpt_id, 0],
            "clip": [ckpt_id, 1],
            "lora_name": lora.name,
            "strength_model": float(strength),
            "strength_clip": float(strength),
        },
    }
    for nid, node in prompt.items():
        if str(nid) == lora_id or not isinstance(node, dict):
            continue
        inputs = node.setdefault("inputs", {})
        for key, val in list(inputs.items()):
            if isinstance(val, list) and len(val) == 2 and str(val[0]) == ckpt_id:
                if val[1] == 0:
                    inputs[key] = [lora_id, 0]
                elif val[1] == 1:
                    inputs[key] = [lora_id, 1]
    return lora.name
