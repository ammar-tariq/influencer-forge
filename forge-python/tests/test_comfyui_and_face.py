import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from forge_python.comfyui_client import ComfyUIClient, denoise_for_prompt
from forge_python.face_seed import embedding_present, extract_face_embedding


def test_video_workflow_mac_safe_defaults() -> None:
    root = Path(__file__).resolve().parents[2] / "src-tauri" / "resources" / "workflows"
    data = json.loads((root / "video_animate.json").read_text(encoding="utf-8"))
    assert data["meta"]["frame_count"] == 12
    assert data["prompt"]["5"]["inputs"]["batch_size"] == 12
    assert data["prompt"]["5"]["inputs"]["width"] <= 384
    assert data["prompt"]["3"]["inputs"]["steps"] <= 12
    assert data["prompt"]["9"]["inputs"]["frame_rate"] == 6


def test_inject_prompt_applies_video_frame_count() -> None:
    client = ComfyUIClient()
    bundle = {
        "meta": {
            "positive_node": "6",
            "negative_node": "7",
            "seed_node": "3",
            "size_node": "5",
            "frame_count": 8,
        },
        "prompt": {
            "3": {"class_type": "KSampler", "inputs": {"seed": 1}},
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": 1, "height": 1, "batch_size": 16},
            },
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "x"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "y"}},
        },
    }
    prompt = client.inject_prompt(bundle, positive="hi", seed=2, width=384, height=640)
    assert prompt["5"]["inputs"]["width"] == 384
    assert prompt["5"]["inputs"]["height"] == 640
    assert prompt["5"]["inputs"]["batch_size"] == 8


def test_shipped_faceid_workflows_include_insightface_model_name() -> None:
    root = Path(__file__).resolve().parents[2] / "src-tauri" / "resources" / "workflows"
    for name in ("image_ipadapter_faceid.json", "video_animate.json"):
        path = root / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        node = data["prompt"]["15"]
        assert node["class_type"] == "IPAdapterInsightFaceLoader"
        assert node["inputs"].get("model_name") == "buffalo_l"


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
        "denoise_default": 0.55,
        "denoise_scene": 0.65,
        "denoise_nsfw": 0.62,
        "denoise_nsfw_scene": 0.68,
    }
    assert denoise_for_prompt(is_nsfw=False, prompt_text="studio headshot", meta=meta) == 0.55
    assert (
        denoise_for_prompt(
            is_nsfw=True,
            prompt_text="full body from behind, bikini, beach",
            meta=meta,
        )
        == 0.68
    )
    # Hard cap — never wipe the face lock with near-txt2img denoise.
    assert (
        denoise_for_prompt(
            is_nsfw=True,
            prompt_text="full body beach",
            meta={"denoise_nsfw_scene": 0.95},
        )
        == 0.72
    )


def test_inject_ipadapter_files(tmp_path: Path) -> None:
    bundle = {
        "meta": {
            "positive_node": "6",
            "negative_node": "7",
            "seed_node": "3",
            "image_node": "10",
            "ipadapter_node": "12",
            "clip_vision_node": "13",
        },
        "prompt": {
            "3": {"class_type": "KSampler", "inputs": {"seed": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "x"}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "y"}},
            "10": {"class_type": "LoadImage", "inputs": {"image": "old.png"}},
            "12": {
                "class_type": "IPAdapterModelLoader",
                "inputs": {"ipadapter_file": "old.bin"},
            },
            "13": {
                "class_type": "CLIPVisionLoader",
                "inputs": {"clip_name": "old.safetensors"},
            },
        },
    }
    client = ComfyUIClient()
    prompt = client.inject_prompt(
        bundle,
        positive="portrait",
        seed=1,
        width=512,
        height=768,
        image_filename="iforge_face_1.png",
        ipadapter_file="ip-adapter-faceid-plusv2_sdxl.bin",
        clip_vision_file="CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
    )
    assert prompt["10"]["inputs"]["image"] == "iforge_face_1.png"
    assert prompt["12"]["inputs"]["ipadapter_file"] == "ip-adapter-faceid-plusv2_sdxl.bin"
    assert (
        prompt["13"]["inputs"]["clip_name"]
        == "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
    )


def test_stage_faceid_mode_keeps_sharp_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    comfy_root = tmp_path / "ComfyUI"
    (comfy_root / "input").mkdir(parents=True)
    monkeypatch.setattr("forge_python.comfyui_client.settings.comfyui_root", comfy_root)
    face = tmp_path / "face.png"
    Image.new("RGB", (200, 300), (90, 40, 40)).save(face)
    client = ComfyUIClient()
    name = client.stage_face_reference(
        face, generation_id=7, width=576, height=1024, mode="faceid"
    )
    staged = comfy_root / "input" / name
    with Image.open(staged) as im:
        # FaceID staging is a square head crop for InsightFace / IP-Adapter.
        assert im.size == (512, 512)


def test_face_embedding_stable(tmp_path: Path) -> None:
    img = tmp_path / "face.png"
    Image.new("RGB", (64, 64), (120, 40, 80)).save(img)
    a = extract_face_embedding(img)
    b = extract_face_embedding(img)
    assert a == b
    assert embedding_present(a)
    assert len(a) == 512


@pytest.mark.asyncio
async def test_face_seed_refuses_plain_txt2img(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Face Seed must not silently fall back to inventing a different person."""
    from forge_python import config
    from forge_python.comfyui_client import ComfyUIClient

    monkeypatch.setattr(config.settings, "data_dir", tmp_path)
    monkeypatch.setattr(config.settings, "media_dir", tmp_path / "media")
    monkeypatch.setattr(config.settings, "generations_dir", tmp_path / "media" / "generations")
    monkeypatch.setattr(config.settings, "thumbnails_dir", tmp_path / "media" / "thumbnails")
    monkeypatch.setattr(config.settings, "uploads_dir", tmp_path / "media" / "uploads")
    config.settings.ensure_directories()
    face = tmp_path / "seed.png"
    Image.new("RGB", (64, 64), (10, 20, 30)).save(face)

    client = ComfyUIClient()
    # generate_via_comfy imports these from readiness at call time.
    monkeypatch.setattr(
        "forge_python.readiness.faceid_weights_present",
        lambda: {"ok": False, "ipadapter_file": None, "clip_vision_file": None},
    )
    monkeypatch.setattr(
        "forge_python.readiness.ipadapter_custom_node_installed",
        lambda: False,
    )

    def fake_load(name: str):
        if name == "image_ipadapter_faceid.json":
            return {"stub": True, "prompt": {}}
        if name == "image_img2img.json":
            return {"stub": True, "prompt": {}}
        return {"stub": False, "model": "sdxl", "prompt": {"1": {}}}

    monkeypatch.setattr(client, "load_workflow_bundle", fake_load)

    with pytest.raises(RuntimeError, match="Refusing plain txt2img"):
        await client.generate_via_comfy(
            generation_id=99,
            prompt_text="full body",
            aspect_ratio="9:16",
            seed=1,
            workflow_type="image",
            face_reference=str(face),
        )


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
