from pathlib import Path

import pytest

from forge_python.readiness import collect_readiness, find_checkpoints, workflow_ready


def test_find_checkpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from forge_python import config

    ckpt_dir = tmp_path / "ComfyUI" / "models" / "checkpoints"
    ckpt_dir.mkdir(parents=True)
    fake = ckpt_dir / "sd_xl_base_1.0.safetensors"
    fake.write_bytes(b"not-a-real-model")
    monkeypatch.setattr(config.settings, "comfyui_root", tmp_path / "ComfyUI")
    monkeypatch.setattr(config.settings, "models_dir", tmp_path / "models")
    monkeypatch.setattr("forge_python.readiness.settings", config.settings)
    found = find_checkpoints()
    assert any(p.name == "sd_xl_base_1.0.safetensors" for p in found)


def test_workflow_ready_true() -> None:
    assert workflow_ready("image_faceid.json") is True


@pytest.mark.asyncio
async def test_collect_readiness_stub_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from forge_python import config

    monkeypatch.setattr(config.settings, "comfyui_root", tmp_path / "missing-comfy")
    monkeypatch.setattr(config.settings, "models_dir", tmp_path / "models")
    monkeypatch.setattr(config.settings, "enable_comfyui", False)
    monkeypatch.setattr(config.settings, "allow_stub_fallback", True)
    monkeypatch.setattr("forge_python.readiness.settings", config.settings)
    data = await collect_readiness()
    assert data["mode"] == "stub"
    assert data["real_ready"] is False
    assert any(item["id"] == "comfyui_source" and item["ok"] is False for item in data["checklist"])
