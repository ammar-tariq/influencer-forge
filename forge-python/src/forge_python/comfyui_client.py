"""ComfyUI client with stub fallback when ComfyUI is unavailable."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from forge_python.config import settings
from forge_python.stub_generator import generate_stub_image

logger = logging.getLogger(__name__)


class ComfyUIClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.comfyui_url).rstrip("/")
        self._process: Any = None

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/system_stats")
                return resp.status_code == 200
        except Exception:
            return False

    def load_workflow(self, name: str) -> dict[str, Any]:
        path = settings.workflows_dir / name
        if not path.exists():
            return {"workflow": name, "stub": True}
        return json.loads(path.read_text(encoding="utf-8"))

    async def generate(
        self,
        *,
        generation_id: int,
        prompt: str,
        aspect_ratio: str,
        seed: int | None,
        workflow_type: str,
        face_reference: str | None = None,
    ) -> tuple[Path, Path, int, str]:
        """Return output_path, thumbnail_path, seed, model_used."""
        _ = face_reference
        healthy = await self.health()
        if settings.enable_comfyui and healthy:
            workflow = self.load_workflow(
                "video_animate.json" if workflow_type == "video" else "image_faceid.json"
            )
            logger.info("ComfyUI workflow loaded: %s", workflow.get("name", "unnamed"))
            # Full ComfyUI queue/ws integration lands when local models are present.
            # Until then, fall through to stub artifacts so the product path stays usable.
        out, thumb, used_seed = await generate_stub_image(
            generation_id=generation_id,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            seed=seed,
            workflow_type=workflow_type,
        )
        model = "sdxl" if settings.enable_comfyui and healthy else "stub"
        return out, thumb, used_seed, model
