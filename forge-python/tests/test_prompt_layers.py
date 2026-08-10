import pytest

from forge_python.llm_manager import expand_prompt, resolve_negative_prompt
from forge_python.prompt_layers import (
    ClothingConflictError,
    resolve_prompt_layers,
    strip_clothing_from_text,
)


def test_wardrobe_strips_clothing_from_notes() -> None:
    layers = resolve_prompt_layers(
        "full body shot, standing, wearing a red dress, soft smile",
        wardrobe_keywords="small cute blue bikini",
        is_nsfw_flag=False,
    )
    assert layers.clothing_from_wardrobe
    assert "red dress" not in layers.scene.lower()
    assert "wearing" not in layers.scene.lower()
    assert "soft smile" in layers.scene
    assert layers.wardrobe_keywords == "small cute blue bikini"


def test_wardrobe_plus_nude_raises() -> None:
    with pytest.raises(ClothingConflictError):
        resolve_prompt_layers(
            "full body, fully nude, no clothing, bedroom",
            wardrobe_keywords="gray hoodie",
        )


def test_wardrobe_beats_notes_in_expand() -> None:
    layers = resolve_prompt_layers(
        "standing, wearing jeans and a hoodie, wind in hair",
        wardrobe_keywords="elegant black evening gown",
    )
    expanded = expand_prompt(
        layers.scene,
        influencer_name="Elena",
        looks_prompt="28-year-old woman",
        wardrobe_keywords=layers.wardrobe_keywords,
        clothing_from_wardrobe=True,
        is_nsfw=False,
        face_locked=True,
    )
    assert "evening gown" in expanded
    assert "jeans" not in expanded.lower()
    assert "same person as reference" in expanded


def test_wardrobe_nsfw_does_not_inject_nude() -> None:
    layers = resolve_prompt_layers(
        "full body, beach, soft smile",
        wardrobe_keywords="micro bikini",
        is_nsfw_flag=True,
    )
    expanded = expand_prompt(
        layers.scene,
        influencer_name="X",
        looks_prompt="woman",
        wardrobe_keywords=layers.wardrobe_keywords,
        clothing_from_wardrobe=True,
        is_nsfw=True,
    )
    assert "bikini" in expanded
    assert ", nude," not in expanded.lower()
    neg = resolve_negative_prompt(
        is_nsfw=True,
        user_prompt=layers.scene,
        wardrobe_keywords=layers.wardrobe_keywords,
        clothing_from_wardrobe=True,
    )
    assert "jeans" in neg


def test_strip_clothing_helper() -> None:
    assert "smile" in strip_clothing_from_text("soft smile, wearing a coat")
    assert "coat" not in strip_clothing_from_text("soft smile, wearing a coat").lower()
