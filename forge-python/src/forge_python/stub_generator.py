"""Phase 1 stub image/video generator using Pillow placeholders."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from forge_python.config import settings

ASPECT_SIZES = {
    "9:16": (576, 1024),
    "16:9": (1024, 576),
    "1:1": (768, 768),
}


async def generate_stub_image(
    *,
    generation_id: int,
    prompt: str,
    aspect_ratio: str,
    seed: int | None,
    workflow_type: str = "image",
) -> tuple[Path, Path, int]:
    """Write a labeled placeholder image and thumbnail; return paths + seed."""
    await asyncio.sleep(0.4)  # simulate work for queue UX
    used_seed = seed if seed is not None else random.randint(1, 2_147_483_647)
    width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])
    color = (
        (30 + (used_seed % 80), 90 + (used_seed % 60), 110 + (used_seed % 90), 255)
        if workflow_type == "image"
        else (90, 40, 70, 255)
    )
    image = Image.new("RGBA", (width, height), color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    label = [
        f"InfluencerForge stub #{generation_id}",
        f"type={workflow_type}",
        f"seed={used_seed}",
        prompt[:120],
    ]
    y = 40
    for line in label:
        draw.text((32, y), line, fill=(245, 245, 245, 255), font=font)
        y += 28

    settings.ensure_directories()
    out = settings.generations_dir / f"{generation_id}.png"
    thumb = settings.thumbnails_dir / f"{generation_id}_thumb.png"
    image.save(out)
    image.resize((min(256, width), int(min(256, width) * height / width))).save(thumb)
    return out, thumb, used_seed
