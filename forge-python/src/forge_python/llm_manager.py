"""LLM prompt expansion (template first, optional cloud/local later)."""

from __future__ import annotations

from typing import Any


def build_system_prompt(name: str, bio: str | None, traits: dict[str, str], niche: str) -> str:
    trait_bits = ", ".join(f"{k}={v}" for k, v in traits.items()) or "friendly"
    bio_text = bio or f"A {niche} creator named {name}."
    return (
        f"You are {name}, an influencer in the {niche} niche. "
        f"Bio: {bio_text} Traits: {trait_bits}. "
        "Write vivid, concise image prompts that match your persona."
    )


def build_looks_prompt(
    *,
    age: int | None,
    ethnicity: str | None,
    hair_color: str | None,
    hair_style: str | None,
    eye_color: str | None,
    style: str | None,
) -> str:
    parts = [
        f"{age}-year-old" if age else None,
        ethnicity,
        f"{hair_color} {hair_style} hair" if hair_color or hair_style else None,
        f"{eye_color} eyes" if eye_color else None,
        f"{style} style" if style else None,
        "highly detailed portrait, consistent face",
    ]
    return ", ".join(p for p in parts if p)


def expand_prompt(
    user_prompt: str,
    *,
    influencer_name: str,
    looks_prompt: str,
    wardrobe_keywords: str | None = None,
    system_prompt: str | None = None,
    provider: str = "template",
) -> str:
    """Expand a short user prompt into a richer generation prompt.

    Phase 1 uses templates. Cloud/local LLM providers can be plugged in later
    via settings without changing callers.
    """
    _ = provider, system_prompt
    wardrobe = f", wearing {wardrobe_keywords}" if wardrobe_keywords else ""
    return (
        f"Portrait of {influencer_name}, {looks_prompt}{wardrobe}, {user_prompt}, "
        "studio lighting, sharp focus, social media quality"
    )


def smart_daily_suggestions(niche: str, scenes: list[str] | None = None) -> list[str]:
    base = scenes or [
        "morning coffee routine",
        "behind the scenes workspace",
        "outfit of the day",
        "weekend lifestyle moment",
    ]
    return [f"{niche}: {scene}" for scene in base]


def resolve_provider_settings(settings_map: dict[str, Any]) -> str:
    return str(settings_map.get("llm_provider", "local"))
