"""ComfyUI client: spawn, prompt queue, history poll, view download, stub fallback."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from forge_python.config import settings
from forge_python.stub_generator import ASPECT_SIZES, generate_stub_image

logger = logging.getLogger(__name__)


class ComfyUIClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.comfyui_url).rstrip("/")
        self._process: subprocess.Popen[bytes] | None = None
        self._client_id = str(uuid.uuid4())

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/system_stats")
                return resp.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    def load_workflow_bundle(self, name: str) -> dict[str, Any]:
        path = settings.workflows_dir / name
        if not path.exists():
            return {"name": name, "stub": True, "prompt": {}, "meta": {}}
        return json.loads(path.read_text(encoding="utf-8"))

    def start_process(self) -> bool:
        """Spawn headless ComfyUI if configured and not already healthy."""
        if not settings.enable_comfyui:
            return False
        root = settings.comfyui_root
        main_py = root / "main.py"
        if not main_py.exists():
            logger.warning("ComfyUI root missing main.py: %s", root)
            return False
        if self._process and self._process.poll() is None:
            return True
        env = os.environ.copy()
        venv_python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python_exec = env.get("IFORGE_COMFYUI_PYTHON") or (
            str(venv_python) if venv_python.exists() else "python3"
        )
        cmd = [
            python_exec,
            str(main_py),
            "--listen",
            "127.0.0.1",
            "--port",
            str(settings.comfyui_port),
        ]
        self._process = subprocess.Popen(
            cmd,
            cwd=str(root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Spawned ComfyUI pid=%s", self._process.pid)
        return True

    def stop_process(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None

    def inject_prompt(
        self,
        bundle: dict[str, Any],
        *,
        positive: str,
        seed: int,
        width: int,
        height: int,
        negative: str = "blurry, low quality, deformed",
        checkpoint_name: str | None = None,
        face_reference: str | None = None,
    ) -> dict[str, Any]:
        prompt = copy.deepcopy(bundle.get("prompt") or {})
        meta = bundle.get("meta") or {}
        pos_node = str(meta.get("positive_node", "6"))
        neg_node = str(meta.get("negative_node", "7"))
        seed_node = str(meta.get("seed_node", "3"))
        size_node = str(meta.get("size_node", "5"))
        ckpt_node = str(meta.get("checkpoint_node", "4"))
        if pos_node in prompt:
            text = positive
            if face_reference:
                text = f"{positive}, consistent face reference:{Path(face_reference).name}"
            prompt[pos_node].setdefault("inputs", {})["text"] = text
        if neg_node in prompt:
            prompt[neg_node].setdefault("inputs", {})["text"] = negative
        if seed_node in prompt:
            prompt[seed_node].setdefault("inputs", {})["seed"] = seed
        if size_node in prompt:
            prompt[size_node].setdefault("inputs", {})["width"] = width
            prompt[size_node].setdefault("inputs", {})["height"] = height
        if checkpoint_name and ckpt_node in prompt:
            prompt[ckpt_node].setdefault("inputs", {})["ckpt_name"] = checkpoint_name
        return prompt

    async def queue_prompt(self, prompt: dict[str, Any]) -> str:
        payload = {"prompt": prompt, "client_id": self._client_id}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/prompt", json=payload)
            resp.raise_for_status()
            data = resp.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI did not return prompt_id: {data}")
        return str(prompt_id)

    async def wait_for_images(self, prompt_id: str, timeout_s: float = 180.0) -> list[dict[str, Any]]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        async with httpx.AsyncClient(timeout=30.0) as client:
            while loop.time() < deadline:
                resp = await client.get(f"{self.base_url}/history/{prompt_id}")
                resp.raise_for_status()
                history = resp.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    images = [
                        img
                        for node_out in outputs.values()
                        for img in node_out.get("images", [])
                    ]
                    if images:
                        return images
                await asyncio.sleep(0.5)
        raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out")

    async def download_image(self, image_info: dict[str, Any], dest: Path) -> Path:
        params = {
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{self.base_url}/view", params=params)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        return dest

    async def generate_via_comfy(
        self,
        *,
        generation_id: int,
        prompt_text: str,
        aspect_ratio: str,
        seed: int,
        workflow_type: str,
        face_reference: str | None = None,
        negative: str | None = None,
    ) -> tuple[Path, Path, int, str]:
        from forge_python.readiness import find_checkpoints

        workflow_name = "video_animate.json" if workflow_type == "video" else "image_faceid.json"
        bundle = self.load_workflow_bundle(workflow_name)
        if bundle.get("stub") and not bundle.get("prompt"):
            raise RuntimeError("Workflow is stub-only")
        checkpoints = find_checkpoints()
        if not checkpoints:
            raise RuntimeError(
                "No diffusion checkpoint found. Place an SDXL .safetensors under "
                f"{settings.comfyui_root / 'models' / 'checkpoints'}"
            )
        width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])
        prompt = self.inject_prompt(
            bundle,
            positive=prompt_text,
            seed=seed,
            width=width,
            height=height,
            negative=negative or "blurry, low quality, deformed",
            checkpoint_name=checkpoints[0].name,
            face_reference=face_reference,
        )
        prompt_id = await self.queue_prompt(prompt)
        images = await self.wait_for_images(prompt_id)
        settings.ensure_directories()
        out = settings.generations_dir / f"{generation_id}.png"
        await self.download_image(images[0], out)
        thumb = settings.thumbnails_dir / f"{generation_id}_thumb.png"
        with Image.open(out) as im:
            rgba = im.convert("RGBA")
            w, h = rgba.size
            tw = 256
            th = max(1, int(256 * h / max(w, 1)))
            rgba.resize((tw, th)).save(thumb)
        model = str(bundle.get("model") or ("animate_diff" if workflow_type == "video" else "sdxl"))
        return out, thumb, seed, model

    async def generate(
        self,
        *,
        generation_id: int,
        prompt: str,
        aspect_ratio: str,
        seed: int | None,
        workflow_type: str,
        face_reference: str | None = None,
        allow_stub: bool | None = None,
        negative: str | None = None,
    ) -> tuple[Path, Path, int, str]:
        """Return output_path, thumbnail_path, seed, model_used."""
        used_seed = seed if seed is not None else int(uuid.uuid4().int % 2_147_483_647)
        stub_ok = settings.allow_stub_fallback if allow_stub is None else allow_stub
        if face_reference:
            logger.info("Face reference attached: %s", face_reference)

        comfy_error: str | None = None
        if settings.enable_comfyui:
            self.start_process()
            for _ in range(20):
                if await self.health():
                    break
                await asyncio.sleep(0.5)
            if await self.health():
                try:
                    return await self.generate_via_comfy(
                        generation_id=generation_id,
                        prompt_text=prompt,
                        aspect_ratio=aspect_ratio,
                        seed=used_seed,
                        workflow_type=workflow_type,
                        face_reference=face_reference,
                        negative=negative,
                    )
                except (httpx.HTTPError, OSError, TimeoutError, RuntimeError, KeyError, ValueError) as exc:
                    logger.exception("ComfyUI generation failed")
                    comfy_error = str(exc)
            else:
                comfy_error = (
                    f"ComfyUI not healthy at {self.base_url}. "
                    f"Install source at {settings.comfyui_root} and ensure port "
                    f"{settings.comfyui_port} is free."
                )
        else:
            comfy_error = "IFORGE_ENABLE_COMFYUI is not set (stub/dev mode)."

        if not stub_ok:
            raise RuntimeError(
                "Real generation unavailable: "
                f"{comfy_error} Set IFORGE_ALLOW_STUB_FALLBACK=1 to allow placeholders, "
                "or finish the readiness checklist at GET /api/readiness."
            )

        out, thumb, stub_seed = await generate_stub_image(
            generation_id=generation_id,
            prompt=prompt + (f" [stub: {comfy_error}]" if comfy_error else ""),
            aspect_ratio=aspect_ratio,
            seed=used_seed,
            workflow_type=workflow_type,
        )
        return out, thumb, stub_seed, "stub"

    async def status(self) -> dict[str, Any]:
        healthy = await self.health()
        return {
            "enabled": settings.enable_comfyui,
            "healthy": healthy,
            "url": self.base_url,
            "root": str(settings.comfyui_root),
            "process_running": bool(self._process and self._process.poll() is None),
        }
