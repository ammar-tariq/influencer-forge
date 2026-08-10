import pytest

from forge_python.config import settings
from forge_python.llm_manager import (
    build_looks_prompt,
    build_system_prompt,
    expand_prompt,
    gender_phrase,
    prompt_implies_nsfw,
    resolve_negative_prompt,
)
from forge_python.stub_generator import generate_stub_image


def test_build_prompts() -> None:
    system = build_system_prompt("Elena", "Tech host", {"tone": "friendly"}, "Tech")
    assert "Elena" in system
    looks = build_looks_prompt(
        age=28,
        ethnicity="Asian",
        hair_color="Black",
        hair_style="Long straight",
        eye_color="Brown",
        style="Casual",
        gender="Female",
        body={"height": "Tall", "breast_size": "Medium", "butt_size": "Round / medium"},
    )
    assert "28-year-old adult woman" in looks
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
    expanded = expand_prompt(
        "full body shot, head to toe visible in frame, fully nude, no clothing, bedroom",
        influencer_name="Natasha",
        looks_prompt=looks,
        is_nsfw=True,
    )
    assert expanded.startswith("full body")
    assert "waist up" not in expanded
    assert "entire subject visible" in expanded
    neg = resolve_negative_prompt(is_nsfw=True)
    assert "bra" in neg


def test_prompt_implies_nsfw() -> None:
    assert prompt_implies_nsfw("Topless")
    assert prompt_implies_nsfw("fully nude beach")
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
