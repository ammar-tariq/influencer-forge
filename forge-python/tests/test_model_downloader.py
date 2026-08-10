import json
from pathlib import Path

import pytest

from forge_python.model_downloader import ModelDownloader


@pytest.mark.asyncio
async def test_bootstrap_skips_models_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from forge_python import config

    monkeypatch.setattr(config.settings, "data_dir", tmp_path)
    monkeypatch.setattr(config.settings, "models_dir", tmp_path / "models")
    monkeypatch.setattr(config.settings, "media_dir", tmp_path / "media")
    monkeypatch.setattr(config.settings, "generations_dir", tmp_path / "media" / "g")
    monkeypatch.setattr(config.settings, "thumbnails_dir", tmp_path / "media" / "t")
    monkeypatch.setattr(config.settings, "vault_dir", tmp_path / "vault")
    monkeypatch.setattr(config.settings, "uploads_dir", tmp_path / "uploads")
    monkeypatch.setattr(config.settings, "enable_model_downloads", False)
    monkeypatch.setattr("forge_python.model_downloader.settings", config.settings)

    dl = ModelDownloader()
    state = await dl.run_bootstrap()
    assert state.ready is True
    assert state.progress == 100
    assert any(s["id"] == "models" and s["status"] == "skipped" for s in state.steps)


@pytest.mark.asyncio
async def test_resumable_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from forge_python import config

    manifest = tmp_path / "models.json"
    dest_rel = "tiny.bin"
    # Local file URL via custom downloader patch — write content through _download_resumable mock path
    source = tmp_path / "source.bin"
    source.write_bytes(b"hello-influencer-forge")
    manifest.write_text(
        json.dumps({"models": [{"name": "tiny", "path": dest_rel, "url": source.as_uri()}]}),
        encoding="utf-8",
    )

    monkeypatch.setattr(config.settings, "data_dir", tmp_path / "data")
    monkeypatch.setattr(config.settings, "models_dir", tmp_path / "data" / "models")
    monkeypatch.setattr(config.settings, "media_dir", tmp_path / "data" / "media")
    monkeypatch.setattr(config.settings, "generations_dir", tmp_path / "data" / "media" / "g")
    monkeypatch.setattr(config.settings, "thumbnails_dir", tmp_path / "data" / "media" / "t")
    monkeypatch.setattr(config.settings, "vault_dir", tmp_path / "data" / "vault")
    monkeypatch.setattr(config.settings, "uploads_dir", tmp_path / "data" / "uploads")
    monkeypatch.setattr(config.settings, "enable_model_downloads", True)
    monkeypatch.setattr(config.settings, "model_manifest_path", manifest)
    monkeypatch.setattr("forge_python.model_downloader.settings", config.settings)

    dl = ModelDownloader()
    state = await dl.run_bootstrap()
    assert state.ready is True
    out = config.settings.models_dir / dest_rel
    assert out.exists()
    assert out.read_bytes() == b"hello-influencer-forge"
