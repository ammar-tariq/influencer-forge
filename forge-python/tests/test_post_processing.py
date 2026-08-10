from pathlib import Path

from PIL import Image

from forge_python.config import settings
from forge_python.post_processing import process_image


def test_process_image_rotate_and_watermark(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "media_dir", tmp_path / "media")
    monkeypatch.setattr(settings, "generations_dir", tmp_path / "media" / "generations")
    settings.ensure_directories()
    src = settings.generations_dir / "7.png"
    Image.new("RGB", (64, 96), (20, 40, 60)).save(src)
    out = process_image(
        src,
        rotate_degrees=90,
        watermark_text="IFORGE",
        overlay_text="Hello",
        generation_id=7,
    )
    assert out.exists()
    assert out.name == "7_edited.png"
    with Image.open(out) as im:
        assert im.size == (96, 64)  # rotated


def test_process_image_crop(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "media_dir", tmp_path / "media")
    monkeypatch.setattr(settings, "generations_dir", tmp_path / "media" / "generations")
    settings.ensure_directories()
    src = settings.generations_dir / "3.png"
    Image.new("RGB", (100, 80), (10, 20, 30)).save(src)
    out = process_image(src, crop=(10, 10, 90, 70), generation_id=3)
    with Image.open(out) as im:
        assert im.size == (80, 60)
