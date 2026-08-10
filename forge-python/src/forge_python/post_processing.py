"""Simple Pillow post-production edits."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from forge_python.config import settings


def process_image(
    source: Path,
    *,
    rotate_degrees: int = 0,
    crop: tuple[int, int, int, int] | None = None,
    watermark_text: str | None = None,
    overlay_text: str | None = None,
    generation_id: int,
) -> Path:
    image = Image.open(source).convert("RGBA")
    if rotate_degrees:
        image = image.rotate(rotate_degrees, expand=True)
    if crop:
        image = image.crop(crop)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    if overlay_text:
        draw.text((24, 24), overlay_text, fill=(255, 255, 255, 230), font=font)
    if watermark_text:
        draw.text(
            (24, image.height - 40),
            watermark_text,
            fill=(255, 255, 255, 160),
            font=font,
        )
    settings.ensure_directories()
    out = settings.generations_dir / f"{generation_id}_edited.png"
    image.save(out)
    return out
