from pathlib import Path

import pytest

from forge_python.readiness import collect_readiness, find_checkpoints, workflow_ready


def test_find_checkpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from forge_python import config

    ckpt_dir = tmp_path / "ComfyUI" / "models" / "checkpoints"
    ckpt_dir.mkdir(parents=True)
    fake = ckpt_dir / "RealVisXL_V5.0_fp16.safetensors"
    # Readiness ignores tiny marker files; create a sparse-ish large file via truncate.
    with fake.open("wb") as fh:
        fh.truncate(120_000_000)
    monkeypatch.setattr(config.settings, "comfyui_root", tmp_path / "ComfyUI")
    monkeypatch.setattr(config.settings, "models_dir", tmp_path / "models")
    monkeypatch.setattr(config.settings, "extra_model_dirs", [])
    monkeypatch.setattr("forge_python.readiness.settings", config.settings)
    found = find_checkpoints()
    assert any(p.name == "RealVisXL_V5.0_fp16.safetensors" for p in found)


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


@pytest.mark.asyncio
async def test_faceid_and_animatediff_optional_checklist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from forge_python import config
    from forge_python.readiness import faceid_weights_present, find_motion_module

    comfy = tmp_path / "ComfyUI"
    (comfy / "custom_nodes" / "ComfyUI_IPAdapter_plus").mkdir(parents=True)
    (comfy / "custom_nodes" / "ComfyUI-AnimateDiff-Evolved").mkdir(parents=True)
    ipa_dir = comfy / "models" / "ipadapter"
    clip_dir = comfy / "models" / "clip_vision"
    motion_dir = comfy / "models" / "animatediff_models"
    for d in (ipa_dir, clip_dir, motion_dir):
        d.mkdir(parents=True)
    (ipa_dir / "ip-adapter-faceid-plusv2_sdxl.bin").write_bytes(b"x" * 2048)
    (clip_dir / "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors").write_bytes(b"y" * 2048)
    motion = motion_dir / "mm_sdxl_v10_beta.safetensors"
    with motion.open("wb") as fh:
        fh.truncate(11_000_000)

    monkeypatch.setattr(config.settings, "comfyui_root", comfy)
    monkeypatch.setattr(config.settings, "models_dir", tmp_path / "models")
    monkeypatch.setattr(config.settings, "extra_model_dirs", [])
    monkeypatch.setattr(config.settings, "enable_comfyui", False)
    monkeypatch.setattr("forge_python.readiness.settings", config.settings)

    weights = faceid_weights_present()
    assert weights["ok"] is True
    assert find_motion_module() is not None

    data = await collect_readiness()
    assert data["faceid_ready"] is True
    assert data["animatediff_ready"] is True
    assert any(i["id"] == "ipadapter_faceid" and i["ok"] for i in data["checklist"])
    assert any(i["id"] == "animatediff" and i["ok"] for i in data["checklist"])
    # Optional extras must not gate core "real" mode by themselves.
    assert data["real_ready"] is False


def test_instantid_weights_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from forge_python import config
    from forge_python.readiness import instantid_custom_node_installed, instantid_weights_present

    comfy = tmp_path / "ComfyUI"
    (comfy / "custom_nodes" / "ComfyUI_InstantID").mkdir(parents=True)
    (comfy / "models" / "instantid").mkdir(parents=True)
    (comfy / "models" / "controlnet").mkdir(parents=True)
    ant = comfy / "models" / "insightface" / "models" / "antelopev2"
    ant.mkdir(parents=True)
    (comfy / "models" / "instantid" / "ip-adapter.bin").write_bytes(b"x" * 2048)
    cn = comfy / "models" / "controlnet" / "instantid_sdxl_controlnet.safetensors"
    with cn.open("wb") as fh:
        fh.truncate(11_000_000)
    (ant / "scrfd_10g_bnkps.onnx").write_bytes(b"z" * 100)

    monkeypatch.setattr(config.settings, "comfyui_root", comfy)
    monkeypatch.setattr(config.settings, "models_dir", tmp_path / "models")
    monkeypatch.setattr(config.settings, "extra_model_dirs", [])
    monkeypatch.setattr("forge_python.readiness.settings", config.settings)

    assert instantid_custom_node_installed() is True
    weights = instantid_weights_present()
    assert weights["ok"] is True
    assert weights["controlnet"] is not None
