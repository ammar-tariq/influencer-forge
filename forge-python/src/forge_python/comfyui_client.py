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
from PIL import Image, ImageFilter

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
            jitter = rng.randint(-14, 14)
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


def _head_crop(src: Image.Image) -> Image.Image:
    sw, sh = src.size
    if sh > sw * 1.15:
        return src.crop((0, 0, sw, int(sh * 0.58)))
    return src


def compose_identity_canvas(
    image: Image.Image,
    width: int,
    height: int,
    *,
    face_height_ratio: float = 0.5,
) -> Image.Image:
    """Build an img2img init that locks the face without locking outfit/pose.

    Strategy:
    1) Heavily blur a cover-fit of the reference (weak scene prior).
    2) Paste a *large sharp* head/shoulders crop in the upper frame.
    Keep denoise moderate (~0.55–0.68) so identity survives full-body scenes.
    """
    src = image.convert("RGB")
    head = _head_crop(src)

    avg = head.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    if not isinstance(avg, tuple):
        avg = (110, 110, 120)
    base = (
        (int(avg[0]) + 150) // 2,
        (int(avg[1]) + 150) // 2,
        (int(avg[2]) + 155) // 2,
    )

    filled = _cover_resize(src, width, height)
    blur_radius = max(18, width // 28)
    soft = filled.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    noise = _soft_noise_canvas(width, height, base)
    canvas = Image.blend(soft, noise, 0.55)

    target_h = max(96, int(height * face_height_ratio))
    scale = target_h / max(head.height, 1)
    tw = max(96, int(head.width * scale))
    th = target_h
    if tw > int(width * 0.88):
        tw = int(width * 0.88)
        th = max(96, int(head.height * (tw / max(head.width, 1))))
    face = head.resize((tw, th), Image.Resampling.LANCZOS)

    # Feathered paste so the head blends into the soft body region.
    mask = Image.new("L", (tw, th), 0)
    mask_px = mask.load()
    assert mask_px is not None
    feather = max(8, min(tw, th) // 12)
    for y in range(th):
        for x in range(tw):
            edge = min(x, y, tw - 1 - x, th - 1 - y)
            alpha = 255 if edge >= feather else int(255 * (edge / feather))
            # Soften bottom edge more so shoulders dissolve into the new body.
            bottom_fade = th - 1 - y
            if bottom_fade < feather * 2:
                alpha = min(alpha, int(255 * (bottom_fade / (feather * 2))))
            mask_px[x, y] = alpha

    x = (width - tw) // 2
    y = max(4, int(height * 0.04))
    canvas.paste(face, (x, y), mask)
    return canvas


def denoise_for_prompt(*, is_nsfw: bool, prompt_text: str, meta: dict[str, Any]) -> float:
    """Moderate denoise only — high values (~0.9) erase face/hair identity."""
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
        value = float(meta.get("denoise_nsfw_scene", 0.68))
    elif is_nsfw:
        value = float(meta.get("denoise_nsfw", 0.62))
    elif scene_change:
        value = float(meta.get("denoise_scene", 0.65))
    else:
        value = float(meta.get("denoise_default", 0.55))
    # Hard cap: above ~0.72 img2img stops behaving like a face lock.
    return min(value, 0.72)


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
        mode: str = "img2img",
    ) -> str:
        """Stage face ref into ComfyUI input/; return filename for LoadImage.

        mode=img2img: soft canvas (pose/clothes free). mode=faceid: sharp head crop.
        """
        src = Path(face_reference)
        if not src.is_file():
            raise FileNotFoundError(f"Face reference missing: {src}")
        input_dir = settings.comfyui_root / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest_name = f"iforge_face_{generation_id}.png"
        dest = input_dir / dest_name
        with Image.open(src) as im:
            if mode == "faceid":
                head = _head_crop(im.convert("RGB"))
                side = max(512, min(768, max(head.size)))
                staged = head.resize((side, side), Image.Resampling.LANCZOS)
            elif cover_fill:
                staged = _cover_resize(im, width, height)
            else:
                staged = compose_identity_canvas(im, width, height)
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
        ipadapter_file: str | None = None,
        clip_vision_file: str | None = None,
    ) -> dict[str, Any]:
        prompt = copy.deepcopy(bundle.get("prompt") or {})
        meta = bundle.get("meta") or {}
        pos_node = str(meta.get("positive_node", "6"))
        neg_node = str(meta.get("negative_node", "7"))
        seed_node = str(meta.get("seed_node", "3"))
        size_node = str(meta.get("size_node", "5"))
        ckpt_node = str(meta.get("checkpoint_node", "4"))
        image_node = str(meta.get("image_node", "10"))
        ipa_node = str(meta.get("ipadapter_node", "12"))
        clip_node = str(meta.get("clip_vision_node", "13"))
        if pos_node in prompt:
            text = positive
            # Only append filename hint for txt2img; img2img/FaceID already load pixels.
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
        if ipadapter_file and ipa_node in prompt:
            prompt[ipa_node].setdefault("inputs", {})["ipadapter_file"] = ipadapter_file
        if clip_vision_file and clip_node in prompt:
            prompt[clip_node].setdefault("inputs", {})["clip_name"] = clip_vision_file
        return prompt

    async def object_info_class_types(self) -> set[str]:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"{self.base_url}/object_info")
                if resp.status_code != 200:
                    return set()
                data = resp.json()
                return set(data.keys()) if isinstance(data, dict) else set()
        except (httpx.HTTPError, OSError, ValueError):
            return set()

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
        media = await self.wait_for_media(prompt_id, timeout_s=timeout_s)
        images = [m for m in media if m.get("kind") == "image"]
        if images:
            return images
        raise TimeoutError(f"ComfyUI prompt {prompt_id} produced no images")

    async def wait_for_media(self, prompt_id: str, timeout_s: float = 240.0) -> list[dict[str, Any]]:
        """Poll history for images and/or video helper suite outputs."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        async with httpx.AsyncClient(timeout=30.0) as client:
            while loop.time() < deadline:
                resp = await client.get(f"{self.base_url}/history/{prompt_id}")
                resp.raise_for_status()
                history = resp.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    found: list[dict[str, Any]] = []
                    for node_out in outputs.values():
                        for img in node_out.get("images", []) or []:
                            found.append({**img, "kind": "image"})
                        for gif in node_out.get("gifs", []) or []:
                            found.append({**gif, "kind": "video"})
                    if found:
                        return found
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
        from forge_python.readiness import (
            faceid_weights_present,
            find_checkpoints,
            find_motion_module,
            ipadapter_custom_node_installed,
        )

        width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])
        use_img2img = False
        use_faceid = False
        image_filename: str | None = None
        denoise: float | None = None
        ipadapter_file: str | None = None
        clip_vision_file: str | None = None
        bundle: dict[str, Any]

        if workflow_type == "video":
            bundle = copy.deepcopy(self.load_workflow_bundle("video_animate.json"))
            motion = find_motion_module()
            meta = bundle.get("meta") or {}
            motion_node = str(meta.get("motion_node", "20"))
            ade_node = str(meta.get("ade_apply_node", "21"))
            seed_node = str(meta.get("seed_node", "3"))
            faceid_nodes = ("10", "12", "13", "14", "15")
            if motion and motion_node in (bundle.get("prompt") or {}):
                bundle["prompt"][motion_node].setdefault("inputs", {})["model_name"] = motion.name
            weights = faceid_weights_present()
            node_ok = ipadapter_custom_node_installed()
            can_faceid = (
                bool(face_reference)
                and Path(face_reference).is_file()
                and weights["ok"]
                and node_ok
            )
            if can_faceid:
                use_faceid = True
                image_filename = self.stage_face_reference(
                    face_reference,
                    generation_id=generation_id,
                    width=width,
                    height=height,
                    mode="faceid",
                )
                ipadapter_file = weights["ipadapter_file"]
                clip_vision_file = weights["clip_vision_file"]
                bundle["model"] = "animate_diff-faceid"
                logger.info(
                    "Using AnimateDiff + FaceID for gen %s (file=%s)",
                    generation_id,
                    image_filename,
                )
            else:
                # Strip FaceID nodes so ComfyUI does not require IPAdapter for plain video.
                prompt_nodes = bundle.setdefault("prompt", {})
                for nid in faceid_nodes:
                    prompt_nodes.pop(nid, None)
                if seed_node in prompt_nodes:
                    prompt_nodes[seed_node].setdefault("inputs", {})["model"] = [
                        ade_node,
                        0,
                    ]
                if face_reference and Path(face_reference).is_file():
                    logger.info(
                        "Video gen %s: FaceID unavailable — AnimateDiff without identity lock",
                        generation_id,
                    )
        elif face_reference and Path(face_reference).is_file():
            weights = faceid_weights_present()
            node_ok = ipadapter_custom_node_installed()
            faceid_bundle = self.load_workflow_bundle("image_ipadapter_faceid.json")
            if (
                weights["ok"]
                and node_ok
                and faceid_bundle.get("prompt")
                and not faceid_bundle.get("stub")
            ):
                use_faceid = True
                image_filename = self.stage_face_reference(
                    face_reference,
                    generation_id=generation_id,
                    width=width,
                    height=height,
                    mode="faceid",
                )
                ipadapter_file = weights["ipadapter_file"]
                clip_vision_file = weights["clip_vision_file"]
                bundle = faceid_bundle
                logger.info(
                    "Using IP-Adapter FaceID for gen %s (file=%s)",
                    generation_id,
                    image_filename,
                )
            else:
                img2img = self.load_workflow_bundle("image_img2img.json")
                if img2img.get("prompt") and not img2img.get("stub"):
                    use_img2img = True
                    image_filename = self.stage_face_reference(
                        face_reference,
                        generation_id=generation_id,
                        width=width,
                        height=height,
                        mode="img2img",
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
        else:
            bundle = self.load_workflow_bundle("image_faceid.json")

        if bundle.get("stub") and not bundle.get("prompt"):
            raise RuntimeError("Workflow is stub-only")
        if workflow_type == "video" and find_motion_module() is None:
            raise RuntimeError(
                "AnimateDiff motion module not found. Install ComfyUI-AnimateDiff-Evolved "
                "and place an mm_sdxl / mm_sd_v15 module under models/animatediff_models."
            )
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
            face_reference=None if (use_img2img or use_faceid) else face_reference,
            image_filename=image_filename,
            denoise=denoise,
            ipadapter_file=ipadapter_file,
            clip_vision_file=clip_vision_file,
        )
        prompt_id = await self.queue_prompt(prompt)
        media = await self.wait_for_media(prompt_id)
        settings.ensure_directories()
        model = str(
            bundle.get("model")
            or ("animate_diff" if workflow_type == "video" else "sdxl")
        )
        video = next((m for m in media if m.get("kind") == "video"), None)
        image = next((m for m in media if m.get("kind") == "image"), None)
        if workflow_type == "video" and video:
            out = settings.generations_dir / f"{generation_id}.mp4"
            await self.download_image(video, out)
            thumb = settings.thumbnails_dir / f"{generation_id}_thumb.png"
            if image:
                frame = settings.generations_dir / f"{generation_id}_frame.png"
                await self.download_image(image, frame)
                with Image.open(frame) as im:
                    rgba = im.convert("RGBA")
                    tw = 256
                    th = max(1, int(256 * rgba.height / max(rgba.width, 1)))
                    rgba.resize((tw, th)).save(thumb)
                try:
                    frame.unlink()
                except OSError:
                    pass
            else:
                # Solid placeholder thumb when only mp4 is returned.
                Image.new("RGB", (256, 456), (40, 48, 56)).save(thumb)
            return out, thumb, seed, model

        if not image:
            raise RuntimeError("ComfyUI returned no usable image/video output")
        out = settings.generations_dir / f"{generation_id}.png"
        await self.download_image(image, out)
        thumb = settings.thumbnails_dir / f"{generation_id}_thumb.png"
        with Image.open(out) as im:
            rgba = im.convert("RGBA")
            w, h = rgba.size
            tw = 256
            th = max(1, int(256 * h / max(w, 1)))
            rgba.resize((tw, th)).save(thumb)
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
