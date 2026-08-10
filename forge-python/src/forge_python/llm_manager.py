"""LLM prompt expansion (template first, optional cloud/local later)."""

from __future__ import annotations

import re
from typing import Any

# Soft cues that the user wants adult / unclothed output.
_EXPLICIT_HINTS = (
    "nude",
    "naked",
    "topless",
    "bottomless",
    "nsfw",
    "explicit",
    "bare breasts",
    "bare chest",
    "no clothes",
    "without clothes",
    "fully nude",
    "lingerie off",
    "undressed",
)

SFW_NEGATIVE = (
    "blurry, low quality, deformed, bad anatomy, extra limbs, watermark, text, logo"
)

# Push the model away from clothing when generating adult content.
NSFW_NEGATIVE = (
    "blurry, low quality, deformed, bad anatomy, extra limbs, watermark, text, logo, "
    "clothes, clothing, dressed, wearing clothes, shirt, blouse, bra, bikini top, "
    "jacket, hoodie, sweater, dress, covered breasts, covered chest, "
    "overly clothed, fabric covering torso"
)


def prompt_implies_nsfw(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _EXPLICIT_HINTS)


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
    for_nsfw: bool = False,
) -> str:
    parts = [
        f"{age}-year-old adult woman" if age else "adult woman",
        ethnicity,
        f"{hair_color} {hair_style} hair" if hair_color or hair_style else None,
        f"{eye_color} eyes" if eye_color else None,
    ]
    if for_nsfw:
        # Avoid fashion/style words that read as "keep clothes on".
        parts.append("same consistent face and body")
    else:
        if style:
            parts.append(f"{style} style")
        parts.append("highly detailed portrait, consistent face")
    return ", ".join(p for p in parts if p)


def expand_prompt(
    user_prompt: str,
    *,
    influencer_name: str,
    looks_prompt: str,
    wardrobe_keywords: str | None = None,
    system_prompt: str | None = None,
    provider: str = "template",
    is_nsfw: bool = False,
) -> str:
    """Expand a short user prompt into a richer generation prompt.

    Phase 1 uses templates. Cloud/local LLM providers can be plugged in later
    via settings without changing callers.
    """
    _ = provider, system_prompt
    scene = user_prompt.strip() or "studio portrait"

    if is_nsfw:
        # Scene intent first so RealVisXL doesn't bury it under "portrait / casual".
        # Prefer waist-up / medium shot so topless/nude is actually visible.
        return (
            f"{scene}, nude, bare skin, uncovered breasts, "
            f"{influencer_name}, {looks_prompt}, "
            f"photorealistic adult photograph, natural skin texture, "
            f"medium shot from waist up, looking at camera, sharp focus, detailed anatomy"
        )

    wardrobe = f", wearing {wardrobe_keywords}" if wardrobe_keywords else ""
    return (
        f"Portrait of {influencer_name}, {looks_prompt}{wardrobe}, {scene}, "
        "studio lighting, sharp focus, social media quality"
    )


def resolve_negative_prompt(*, is_nsfw: bool, custom: str | None = None) -> str:
    if custom and custom.strip():
        return custom.strip()
    return NSFW_NEGATIVE if is_nsfw else SFW_NEGATIVE


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


def strip_clothing_style(looks_prompt: str) -> str:
    """Legacy helper: drop trailing 'X style' fashion tokens from stored looks prompts."""
    return re.sub(r",\s*[^,]+ style\b", "", looks_prompt, flags=re.IGNORECASE)
