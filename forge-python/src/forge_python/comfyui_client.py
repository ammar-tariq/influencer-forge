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


def _cover_resize(image: Image.Image, width: int, height: int) -> Image.Image:
    """Resize/crop to exact size while covering the frame (center crop)."""
    src = image.convert("RGB")
    sw, sh = src.size
    if sw <= 0 or sh <= 0:
        return Image.new("RGB", (width, height), (128, 128, 128))
    scale = max(width / sw, height / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - width) // 2)
    top = max(0, (nh - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def _soft_noise_canvas(width: int, height: int, base: tuple[int, int, int]) -> Image.Image:
    """Neutral backdrop so img2img can invent body/scene outside the face patch."""
    import random

    rng = random.Random(width * 1009 + height * 9176 + sum(base))
    canvas = Image.new("RGB", (width, height), base)
    px = canvas.load()
    assert px is not None
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            jitter = rng.randint(-18, 18)
            r = max(0, min(255, base[0] + jitter))
            g = max(0, min(255, base[1] + jitter))
            b = max(0, min(255, base[2] + jitter))
            px[x, y] = (r, g, b)
            if x + 1 < width:
                px[x + 1, y] = (r, g, b)
            if y + 1 < height:
                px[x, y + 1] = (r, g, b)
                if x + 1 < width:
                    px[x + 1, y + 1] = (r, g, b)
    return canvas


def compose_identity_canvas(
    image: Image.Image,
    width: int,
    height: int,
    *,
    face_height_ratio: float = 0.36,
) -> Image.Image:
    """Place the locked face on a soft canvas instead of cover-filling the frame.

    Cover-resizing a waist-up portrait to 9:16 locks pose/clothes into img2img.
    A smaller upper-face patch keeps identity while letting the prompt drive scene.
    """
    src = image.convert("RGB")
    # Prefer a head/shoulders crop from the upper portion of portrait refs.
    sw, sh = src.size
    if sh > sw * 1.15:
        head = src.crop((0, 0, sw, int(sh * 0.62)))
    else:
        head = src

    avg = head.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    if not isinstance(avg, tuple):
        avg = (110, 110, 120)
    base = (int(avg[0]), int(avg[1]), int(avg[2]))
    # Pull backdrop toward neutral so clothing colors don't dominate.
    base = (
        (base[0] + 140) // 2,
        (base[1] + 140) // 2,
        (base[2] + 145) // 2,
    )
    canvas = _soft_noise_canvas(width, height, base)

    target_h = max(64, int(height * face_height_ratio))
    scale = target_h / max(head.height, 1)
    tw = max(64, int(head.width * scale))
    th = target_h
    # Keep face from overflowing width.
    if tw > int(width * 0.72):
        tw = int(width * 0.72)
        th = max(64, int(head.height * (tw / max(head.width, 1))))
    face = head.resize((tw, th), Image.Resampling.LANCZOS)
    x = (width - tw) // 2
    y = max(8, int(height * 0.06))
    canvas.paste(face, (x, y))
    return canvas


def denoise_for_prompt(*, is_nsfw: bool, prompt_text: str, meta: dict[str, Any]) -> float:
    """Higher denoise when the user asks for a big scene/pose change vs the lock shot."""
    lowered = prompt_text.lower()
    scene_change = any(
        token in lowered
        for token in (
            "full body",
            "from behind",
            "over shoulder",
            "bikini",
            "swimsuit",
            "nude",
            "naked",
            "topless",
            "walking",
            "lying",
            "sitting",
            "kneeling",
            "beach",
            "bedroom",
            "outdoors",
        )
    )
    if is_nsfw and scene_change:
        return float(meta.get("denoise_nsfw_scene", meta.get("denoise_nsfw", 0.92)))
    if is_nsfw:
        return float(meta.get("denoise_nsfw", 0.88))
    if scene_change:
        return float(meta.get("denoise_scene", 0.88))
    return float(meta.get("denoise_default", 0.8))


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

    def stage_face_reference(
        self,
        face_reference: str | Path,
        *,
        generation_id: int,
        width: int,
        height: int,
        cover_fill: bool = False,
    ) -> str:
        """Stage face ref into ComfyUI input/; return filename for LoadImage.

        Default pads a head crop onto a soft canvas so img2img does not lock the
        reference photo's crop, pose, and clothing into the new scene.
        """
        src = Path(face_reference)
        if not src.is_file():
            raise FileNotFoundError(f"Face reference missing: {src}")
        input_dir = settings.comfyui_root / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest_name = f"iforge_face_{generation_id}.png"
        dest = input_dir / dest_name
        with Image.open(src) as im:
            staged = (
                _cover_resize(im, width, height)
                if cover_fill
                else compose_identity_canvas(im, width, height)
            )
            staged.save(dest)
        return dest_name

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
        image_filename: str | None = None,
        denoise: float | None = None,
    ) -> dict[str, Any]:
        prompt = copy.deepcopy(bundle.get("prompt") or {})
        meta = bundle.get("meta") or {}
        pos_node = str(meta.get("positive_node", "6"))
        neg_node = str(meta.get("negative_node", "7"))
        seed_node = str(meta.get("seed_node", "3"))
        size_node = str(meta.get("size_node", "5"))
        ckpt_node = str(meta.get("checkpoint_node", "4"))
        image_node = str(meta.get("image_node", "10"))
        if pos_node in prompt:
            text = positive
            # Only append filename hint for txt2img; img2img already loads the pixels.
            if face_reference and not image_filename:
                text = f"{positive}, consistent face reference:{Path(face_reference).name}"
            prompt[pos_node].setdefault("inputs", {})["text"] = text
        if neg_node in prompt:
            prompt[neg_node].setdefault("inputs", {})["text"] = negative
        if seed_node in prompt:
            prompt[seed_node].setdefault("inputs", {})["seed"] = seed
            if denoise is not None:
                prompt[seed_node].setdefault("inputs", {})["denoise"] = float(denoise)
        if size_node in prompt:
            prompt[size_node].setdefault("inputs", {})["width"] = width
            prompt[size_node].setdefault("inputs", {})["height"] = height
        if checkpoint_name and ckpt_node in prompt:
            prompt[ckpt_node].setdefault("inputs", {})["ckpt_name"] = checkpoint_name
        if image_filename and image_node in prompt:
            prompt[image_node].setdefault("inputs", {})["image"] = image_filename
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
        is_nsfw: bool = False,
    ) -> tuple[Path, Path, int, str]:
        from forge_python.readiness import find_checkpoints

        width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])
        use_img2img = False
        image_filename: str | None = None
        denoise: float | None = None

        if workflow_type != "video" and face_reference and Path(face_reference).is_file():
            img2img = self.load_workflow_bundle("image_img2img.json")
            if img2img.get("prompt") and not img2img.get("stub"):
                use_img2img = True
                image_filename = self.stage_face_reference(
                    face_reference,
                    generation_id=generation_id,
                    width=width,
                    height=height,
                )
                meta = img2img.get("meta") or {}
                denoise = denoise_for_prompt(
                    is_nsfw=is_nsfw, prompt_text=prompt_text, meta=meta
                )
                bundle = img2img
                logger.info(
                    "Using img2img face lock for gen %s (denoise=%.2f, file=%s)",
                    generation_id,
                    denoise,
                    image_filename,
                )
            else:
                bundle = self.load_workflow_bundle("image_faceid.json")
        elif workflow_type == "video":
            bundle = self.load_workflow_bundle("video_animate.json")
        else:
            bundle = self.load_workflow_bundle("image_faceid.json")

        if bundle.get("stub") and not bundle.get("prompt"):
            raise RuntimeError("Workflow is stub-only")
        checkpoints = find_checkpoints()
        if not checkpoints:
            raise RuntimeError(
                "No diffusion checkpoint found. Place an SDXL .safetensors under "
                f"{settings.comfyui_root / 'models' / 'checkpoints'}"
            )
        prompt = self.inject_prompt(
            bundle,
            positive=prompt_text,
            seed=seed,
            width=width,
            height=height,
            negative=negative or "blurry, low quality, deformed",
            checkpoint_name=checkpoints[0].name,
            face_reference=None if use_img2img else face_reference,
            image_filename=image_filename,
            denoise=denoise,
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
        model = str(
            bundle.get("model")
            or ("animate_diff" if workflow_type == "video" else "sdxl")
        )
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
        is_nsfw: bool = False,
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
                        is_nsfw=is_nsfw,
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
        # Keep face lock visible even in stub mode when a reference exists.
        if face_reference and Path(face_reference).is_file():
            try:
                with Image.open(face_reference) as face, Image.open(out) as canvas:
                    target = canvas.convert("RGBA")
                    fw = max(64, target.width // 3)
                    face_rgba = face.convert("RGBA").resize(
                        (fw, int(fw * face.height / max(face.width, 1)))
                    )
                    target.paste(face_rgba, (16, 16), face_rgba)
                    target.save(out)
                    tw = 256
                    th = max(1, int(256 * target.height / max(target.width, 1)))
                    target.resize((tw, th)).save(thumb)
            except OSError:
                pass
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
