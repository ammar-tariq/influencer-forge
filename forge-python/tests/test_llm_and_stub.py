import pytest

from forge_python.config import settings
from forge_python.llm_manager import (
    build_looks_prompt,
    build_system_prompt,
    expand_prompt,
    gender_phrase,
    prompt_implies_nsfw,
    prompt_requests_revealing_outfit,
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


def test_face_locked_looks_omit_hair_text() -> None:
    """Wizard 'Red Bob' must not override a curly lock photo."""
    locked = build_looks_prompt(
        age=30,
        ethnicity="Mixed / Multiracial",
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
    assert "Fit" in locked
    assert "30-year-old" in locked


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
