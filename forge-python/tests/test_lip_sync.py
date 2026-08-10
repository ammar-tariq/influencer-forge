from pathlib import Path

import pytest
from PIL import Image

from forge_python.lip_sync import ffmpeg_available, generate_talking_head, resolve_audio_path


def test_ffmpeg_available() -> None:
    # CI / this machine should have ffmpeg for talking-head.
    assert isinstance(ffmpeg_available(), bool)


def test_resolve_audio_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from forge_python import config

    monkeypatch.setattr(config.settings, "data_dir", tmp_path)
    monkeypatch.setattr(config.settings, "uploads_dir", tmp_path / "media" / "uploads")
    config.settings.uploads_dir.mkdir(parents=True)
    audio = config.settings.uploads_dir / "clip.wav"
    audio.write_bytes(b"RIFF....")
    assert resolve_audio_path(str(audio)) == audio.resolve()
    assert resolve_audio_path("clip.wav") == audio.resolve()
    assert resolve_audio_path("missing.wav") is None


@pytest.mark.asyncio
async def test_generate_talking_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not ffmpeg_available():
        pytest.skip("ffmpeg not installed")
    from forge_python import config

    monkeypatch.setattr(config.settings, "data_dir", tmp_path)
    monkeypatch.setattr(config.settings, "media_dir", tmp_path / "media")
    monkeypatch.setattr(config.settings, "generations_dir", tmp_path / "media" / "generations")
    monkeypatch.setattr(config.settings, "thumbnails_dir", tmp_path / "media" / "thumbnails")
    monkeypatch.setattr(config.settings, "uploads_dir", tmp_path / "media" / "uploads")
    config.settings.ensure_directories()

    face = tmp_path / "face.png"
    Image.new("RGB", (128, 160), (40, 80, 120)).save(face)
    # Minimal valid-ish wav via ffmpeg sine tone
    audio = tmp_path / "tone.wav"
    import asyncio
    import shutil

    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg
    proc = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=0.4",
        str(audio),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    assert audio.is_file()

    out, thumb, seed, model = await generate_talking_head(
        generation_id=42,
        face_image=face,
        audio_path=audio,
        aspect_ratio="9:16",
        seed=7,
    )
    assert out.exists() and out.suffix == ".mp4"
    assert thumb.exists()
    assert seed == 7
    assert model == "talking_head_ffmpeg"
