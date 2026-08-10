import pytest

from forge_python.config import settings
from forge_python.llm_manager import (
    build_looks_prompt,
    build_system_prompt,
    expand_prompt,
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
    )
    assert "28-year-old" in looks
    expanded = expand_prompt(
        "morning coffee",
        influencer_name="Elena",
        looks_prompt=looks,
        wardrobe_keywords="gray hoodie",
    )
    assert "morning coffee" in expanded
    assert "gray hoodie" in expanded


def test_nsfw_expansion_puts_scene_first_and_drops_fashion_style() -> None:
    looks = build_looks_prompt(
        age=20,
        ethnicity="Caucasian",
        hair_color="Brown",
        hair_style="Long straight",
        eye_color="Brown",
        style="Casual",
        for_nsfw=True,
    )
    assert "Casual" not in looks
    assert "portrait" not in looks.lower()
    expanded = expand_prompt(
        "Topless",
        influencer_name="Natasha",
        looks_prompt=looks,
        wardrobe_keywords="hoodie",
        is_nsfw=True,
    )
    assert expanded.startswith("Topless")
    assert "nude" in expanded
    assert "waist up" in expanded
    assert "hoodie" not in expanded
    assert "Casual style" not in expanded
    neg = resolve_negative_prompt(is_nsfw=True)
    assert "bra" in neg
    assert "shirt" in neg


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
