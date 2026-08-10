import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from forge_python.comfyui_client import ComfyUIClient, denoise_for_prompt
from forge_python.face_seed import embedding_present, extract_face_embedding


def test_inject_prompt_updates_nodes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    bundle = {
        "name": "t",
        "meta": {
            "positive_node": "6",
            "negative_node": "7",
            "seed_node": "3",
            "size_node": "5",
        },
        "prompt": {
            "3": {"class_type": "KSampler", "inputs": {"seed": 1}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1, "height": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "x"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "y"}},
        },
    }
    (workflows / "image_faceid.json").write_text(json.dumps(bundle), encoding="utf-8")
    monkeypatch.setattr("forge_python.comfyui_client.settings.workflows_dir", workflows)
    client = ComfyUIClient()
    loaded = client.load_workflow_bundle("image_faceid.json")
    prompt = client.inject_prompt(
        loaded, positive="hello world", seed=99, width=512, height=768
    )
    assert prompt["6"]["inputs"]["text"] == "hello world"
    assert prompt["3"]["inputs"]["seed"] == 99
    assert prompt["5"]["inputs"]["width"] == 512
    assert prompt["5"]["inputs"]["height"] == 768


def test_stage_face_and_img2img_inject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    comfy_root = tmp_path / "ComfyUI"
    (comfy_root / "input").mkdir(parents=True)
    monkeypatch.setattr("forge_python.comfyui_client.settings.comfyui_root", comfy_root)
    face = tmp_path / "face.png"
    Image.new("RGB", (200, 300), (90, 40, 40)).save(face)
    client = ComfyUIClient()
    name = client.stage_face_reference(face, generation_id=42, width=576, height=1024)
    assert name == "iforge_face_42.png"
    staged = comfy_root / "input" / name
    assert staged.exists()
    with Image.open(staged) as im:
        assert im.size == (576, 1024)
        # Soft canvas — bottom corners must not be solid face color (cover-fill bug).
        assert im.getpixel((8, 1000)) != (90, 40, 40)

    bundle = {
        "meta": {
            "positive_node": "6",
            "negative_node": "7",
            "seed_node": "3",
            "image_node": "10",
            "checkpoint_node": "4",
        },
        "prompt": {
            "3": {"class_type": "KSampler", "inputs": {"seed": 1, "denoise": 0.5}},
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "x.safetensors"}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "x"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "y"}},
            "10": {"class_type": "LoadImage", "inputs": {"image": "old.png"}},
        },
    }
    prompt = client.inject_prompt(
        bundle,
        positive="topless",
        seed=7,
        width=576,
        height=1024,
        image_filename=name,
        denoise=0.82,
        checkpoint_name="RealVisXL_V5.0_fp16.safetensors",
    )
    assert prompt["10"]["inputs"]["image"] == name
    assert prompt["3"]["inputs"]["denoise"] == 0.82
    assert prompt["4"]["inputs"]["ckpt_name"] == "RealVisXL_V5.0_fp16.safetensors"
    assert "consistent face reference" not in prompt["6"]["inputs"]["text"]


def test_denoise_ramps_for_scene_change() -> None:
    meta = {
        "denoise_default": 0.8,
        "denoise_scene": 0.88,
        "denoise_nsfw": 0.9,
        "denoise_nsfw_scene": 0.94,
    }
    assert denoise_for_prompt(is_nsfw=False, prompt_text="studio headshot", meta=meta) == 0.8
    assert (
        denoise_for_prompt(
            is_nsfw=True,
            prompt_text="full body from behind, bikini, beach",
            meta=meta,
        )
        == 0.94
    )


def test_face_embedding_stable(tmp_path: Path) -> None:
    img = tmp_path / "face.png"
    Image.new("RGB", (64, 64), (120, 40, 80)).save(img)
    a = extract_face_embedding(img)
    b = extract_face_embedding(img)
    assert a == b
    assert embedding_present(a)
    assert len(a) == 512


@pytest.mark.asyncio
async def test_queue_prompt_and_history(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ComfyUIClient(base_url="http://comfy.test")

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            assert url.endswith("/prompt")
            assert "prompt" in json
            return FakeResp({"prompt_id": "abc"})

        async def get(self, url, params=None):
            if "/history/" in url:
                return FakeResp(
                    {
                        "abc": {
                            "outputs": {
                                "9": {
                                    "images": [
                                        {
                                            "filename": "out.png",
                                            "subfolder": "",
                                            "type": "output",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                )
            raise AssertionError(url)

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    prompt_id = await client.queue_prompt({"6": {"inputs": {"text": "hi"}}})
    assert prompt_id == "abc"
    images = await client.wait_for_images(prompt_id, timeout_s=2)
    assert images[0]["filename"] == "out.png"
