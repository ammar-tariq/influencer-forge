import pytest

from forge_python.config import settings
import httpx

from forge_python.llm_manager import (
    build_looks_prompt,
    build_system_prompt,
    claude_enrich_scene,
    enrich_scene_for_provider,
    expand_prompt,
    gender_phrase,
    gemini_enrich_scene,
    llama_enrich_scene,
    openai_enrich_scene,
    prompt_implies_nsfw,
    prompt_requests_revealing_outfit,
    resolve_local_gguf_path,
    resolve_negative_prompt,
)
from forge_python.stub_generator import generate_stub_image


def test_build_prompts() -> None:
    system = build_system_prompt("Elena", "Tech host", {"tone": "friendly"}, "Tech")
    assert "Elena" in system
    looks = build_looks_prompt(
        age=28,
        ethnicity="East Asian",
        nationality="Chinese",
        hair_color="Black",
        hair_style="Long straight",
        eye_color="Brown",
        style="Casual",
        gender="Female",
        body={"height": "Tall", "breast_size": "Medium", "butt_size": "Round / medium"},
    )
    assert "28-year-old woman" in looks
    assert "Chinese nationality" in looks
    assert "breast size: Medium" in looks
    expanded = expand_prompt(
        "full body shot, standing, casual outfit",
        influencer_name="Elena",
        looks_prompt=looks,
        wardrobe_keywords="gray hoodie",
    )
    assert "full body" in expanded
    assert "gray hoodie" in expanded
    assert not expanded.lower().startswith("portrait of")


def test_gender_and_body_for_male() -> None:
    assert gender_phrase("Trans girl") == "trans woman, feminine presentation"
    looks = build_looks_prompt(
        age=30,
        ethnicity="Caucasian",
        hair_color="Brown",
        hair_style="Short",
        eye_color="Blue",
        style=None,
        gender="Male",
        body={"chest": "Broad chest", "height": "Tall"},
        for_nsfw=True,
    )
    assert "man" in looks
    assert "chest: Broad chest" in looks


def test_nsfw_expansion_respects_full_body_scene() -> None:
    looks = build_looks_prompt(
        age=20,
        ethnicity="Caucasian",
        hair_color="Brown",
        hair_style="Long straight",
        eye_color="Brown",
        style="Casual",
        gender="Female",
        body={"breast_size": "Full / large"},
        for_nsfw=True,
    )
    scene = "full body shot, head to toe visible in frame, fully nude, no clothing, bedroom"
    expanded = expand_prompt(
        scene,
        influencer_name="Natasha",
        looks_prompt=looks,
        is_nsfw=True,
    )
    assert "full body" in expanded
    assert "photorealistic" in expanded
    neg = resolve_negative_prompt(is_nsfw=True, user_prompt=scene)
    assert "shirt" in neg
    assert "cartoon" in neg


def test_openai_enrich_requires_key() -> None:
    assert openai_enrich_scene("beach stroll", api_key="") is None


def test_claude_and_gemini_enrich_require_key() -> None:
    assert claude_enrich_scene("beach stroll", api_key="") is None
    assert gemini_enrich_scene("beach stroll", api_key="") is None


def test_claude_enrich_success(monkeypatch) -> None:
    class FakeResp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"content": [{"type": "text", "text": "soft daylight, coastal walk"}]}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def post(self, *args, **kwargs):
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    assert claude_enrich_scene("beach", api_key="sk-ant-test") == "soft daylight, coastal walk"


def test_gemini_enrich_success(monkeypatch) -> None:
    class FakeResp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "candidates": [
                    {"content": {"parts": [{"text": "golden hour, boardwalk stroll"}]}}
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def post(self, *args, **kwargs):
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    assert gemini_enrich_scene("beach", api_key="gem-test") == "golden hour, boardwalk stroll"


def test_enrich_scene_for_provider_routes_keys() -> None:
    text, used = enrich_scene_for_provider(
        "claude",
        "scene",
        settings_map={"anthropic_api_key": ""},
    )
    assert text is None
    assert used == "template"


def test_resolve_local_gguf_path(tmp_path, monkeypatch) -> None:
    from forge_python import config
    from forge_python import llm_manager

    monkeypatch.setattr(config.settings, "models_dir", tmp_path / "models")
    config.settings.ensure_directories()
    gguf = config.settings.models_dir / "llm" / "tiny.gguf"
    gguf.write_bytes(b"gguf-fake")
    assert resolve_local_gguf_path({}) == gguf.resolve()
    custom = tmp_path / "custom.gguf"
    custom.write_bytes(b"x")
    assert (
        resolve_local_gguf_path({"llm_local_model": str(custom)}) == custom.resolve()
    )
    # Relative to models_dir
    rel = config.settings.models_dir / "llm" / "rel.gguf"
    rel.write_bytes(b"y")
    assert (
        resolve_local_gguf_path({"llm_local_model": "llm/rel.gguf"}) == rel.resolve()
    )
    llm_manager._llama_instances.clear()


def test_llama_enrich_without_package_returns_none(tmp_path, monkeypatch) -> None:
    from forge_python import llm_manager

    gguf = tmp_path / "m.gguf"
    gguf.write_bytes(b"x")
    monkeypatch.setitem(__import__("sys").modules, "llama_cpp", None)

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "llama_cpp" or name.startswith("llama_cpp."):
            raise ImportError("no llama")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    llm_manager._llama_instances.clear()
    assert llama_enrich_scene("beach", model_path=gguf) is None


def test_llama_enrich_success(monkeypatch, tmp_path) -> None:
    from forge_python import llm_manager

    gguf = tmp_path / "m.gguf"
    gguf.write_bytes(b"x")

    class FakeLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_chat_completion(self, *args, **kwargs):
            return {"choices": [{"message": {"content": "soft light, cafe window"}}]}

    import types

    fake_mod = types.ModuleType("llama_cpp")
    fake_mod.Llama = FakeLlama  # type: ignore[attr-defined]
    monkeypatch.setitem(__import__("sys").modules, "llama_cpp", fake_mod)
    llm_manager._llama_instances.clear()
    assert llama_enrich_scene("cafe", model_path=gguf) == "soft light, cafe window"
    text, used = enrich_scene_for_provider(
        "local",
        "cafe",
        settings_map={"llm_local_model": str(gguf)},
    )
    assert text == "soft light, cafe window"
    assert used == "local_llama3.2"


def test_nsfw_toggle_keeps_clothed_scene() -> None:
    looks = "12-year-old girl, Caucasian"
    scene = "full body shot, standing, wearing casual everyday outfit, studio"
    expanded = expand_prompt(
        scene,
        influencer_name="Natasha",
        looks_prompt=looks,
        is_nsfw=True,
    )
    assert "casual everyday outfit" in expanded
    assert ", nude," not in expanded.lower()
    assert "bare skin" not in expanded.lower()


def test_bikini_prompt_does_not_force_nude() -> None:
    looks = "25-year-old adult woman, Caucasian"
    scene = "full body from behind, looking over shoulder, wearing a bikini swimsuit, sunny beach"
    expanded = expand_prompt(
        scene,
        influencer_name="Xz",
        looks_prompt=looks,
        is_nsfw=True,
    )
    assert "bikini" in expanded
    assert ", nude," not in expanded.lower()
    assert "bare skin" not in expanded.lower()
    assert prompt_requests_revealing_outfit(scene)
    neg = resolve_negative_prompt(is_nsfw=True, user_prompt=scene)
    assert "jeans" in neg
    assert "bikini" not in neg


def test_face_locked_prompt_leads_with_identity() -> None:
    expanded = expand_prompt(
        "full body beach",
        influencer_name="Xz",
        looks_prompt="25-year-old adult woman, Brown Long straight hair",
        is_nsfw=False,
        face_locked=True,
    )
    assert expanded.startswith("same person as reference photo")
    assert "same hair color and hairstyle" in expanded
    assert expanded.index("identical face") < expanded.index("full body beach")


def test_youth_looks_keep_height_drop_adult_body() -> None:
    looks = build_looks_prompt(
        age=12,
        ethnicity="Caucasian",
        hair_color="Brown",
        hair_style="Long",
        eye_color="Blue",
        style="Casual",
        gender="Female",
        body={
            "height": 'Petite (under 5\'3" / 160cm)',
            "body_type": "Hourglass",
            "breast_size": "Full / large",
            "butt_size": "Very large",
            "hips": "Wide hips",
            "waist": "Narrow waist",
        },
    )
    assert "12-year-old girl" in looks
    assert "woman" not in looks
    assert "Petite" in looks
    assert "true-to-age stature" in looks
    assert "age-accurate 12-year-old body" in looks
    assert "breast" not in looks.lower()
    assert "butt" not in looks.lower()
    assert "Wide hips" not in looks
    assert "Hourglass" not in looks
    assert "slim youthful" in looks
    neg = resolve_negative_prompt(is_nsfw=False, age=12)
    assert "adult body" in neg
    assert "large breasts" in neg


def test_face_locked_looks_body_only() -> None:
    """Face Seed owns face/hair/ethnicity — text keeps body sliders only."""
    locked = build_looks_prompt(
        age=30,
        ethnicity="Mixed / Multiracial",
        nationality="Pakistani",
        hair_color="Red",
        hair_style="Bob",
        eye_color="Green",
        style="Sporty",
        gender="Female",
        body={"body_type": "Fit", "body_hair": "Hairy", "breast_size": "Very large"},
        face_locked=True,
    )
    assert "Bob" not in locked
    assert "Green" not in locked
    assert "Sporty" not in locked
    assert "Hairy" not in locked
    assert "Pakistani" not in locked
    assert "Mixed" not in locked
    assert "30-year-old" not in locked
    assert "woman" not in locked
    assert "Fit" in locked
    assert "Very large" in locked


def test_prompt_implies_nsfw() -> None:
    assert prompt_implies_nsfw("Topless")
    assert prompt_implies_nsfw("fully nude beach")
    assert prompt_implies_nsfw("bikini on the beach")
    assert not prompt_implies_nsfw("golden hour portrait outdoors")


@pytest.mark.asyncio
async def test_stub_generator(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "media_dir", tmp_path / "media")
    monkeypatch.setattr(settings, "generations_dir", tmp_path / "media" / "generations")
    monkeypatch.setattr(settings, "thumbnails_dir", tmp_path / "media" / "thumbnails")
    settings.ensure_directories()
    out, thumb, seed = await generate_stub_image(
        generation_id=1,
        prompt="test prompt",
        aspect_ratio="1:1",
        seed=42,
    )
    assert out.exists()
    assert thumb.exists()
    assert seed == 42
