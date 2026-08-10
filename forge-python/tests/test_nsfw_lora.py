from pathlib import Path

from forge_python.nsfw_lora import apply_nsfw_lora, find_nsfw_lora


def test_find_and_apply_nsfw_lora(tmp_path: Path, monkeypatch) -> None:
    from forge_python import config

    loras = tmp_path / "loras"
    loras.mkdir()
    weight = loras / "my_nsfw_style.safetensors"
    weight.write_bytes(b"0" * 2048)
    monkeypatch.setattr(config.settings, "comfyui_root", tmp_path / "missing")
    monkeypatch.setattr(config.settings, "models_dir", tmp_path)
    monkeypatch.setattr(config.settings, "extra_model_dirs", [])

    found = find_nsfw_lora()
    assert found == weight

    prompt = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "x.safetensors"}},
        "3": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "seed": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 1], "text": "hi"}},
    }
    name = apply_nsfw_lora(prompt)
    assert name == "my_nsfw_style.safetensors"
    assert any(n.get("class_type") == "LoraLoader" for n in prompt.values())
    assert prompt["3"]["inputs"]["model"][1] == 0
    assert prompt["3"]["inputs"]["model"][0] != "4"
    assert prompt["6"]["inputs"]["clip"][0] != "4"
