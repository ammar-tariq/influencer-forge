import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from forge_python.comfyui_client import ComfyUIClient
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
