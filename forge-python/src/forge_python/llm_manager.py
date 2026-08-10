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

_GENDER_PHRASE = {
    "female": "woman",
    "male": "man",
    "trans girl": "trans woman, feminine presentation",
}

SFW_NEGATIVE = (
    "blurry, low quality, deformed, bad anatomy, extra limbs, watermark, text, logo, "
    "cropped head only, extreme close-up face only"
)

# Push the model away from clothing when generating adult content.
NSFW_NEGATIVE = (
    "blurry, low quality, deformed, bad anatomy, extra limbs, watermark, text, logo, "
    "clothes, clothing, dressed, wearing clothes, shirt, blouse, bra, bikini top, "
    "jacket, hoodie, sweater, dress, covered breasts, covered chest, "
    "overly clothed, fabric covering torso, cropped head only"
)


def prompt_implies_nsfw(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _EXPLICIT_HINTS)


def gender_phrase(gender: str | None) -> str:
    if not gender:
        return "woman"
    key = gender.strip().lower()
    return _GENDER_PHRASE.get(key, key)


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
    gender: str | None = None,
    body: dict[str, str] | None = None,
    for_nsfw: bool = False,
) -> str:
    person = gender_phrase(gender)
    parts: list[str | None] = [
        f"{age}-year-old adult {person}" if age else f"adult {person}",
        ethnicity,
        f"{hair_color} {hair_style} hair" if hair_color or hair_style else None,
        f"{eye_color} eyes" if eye_color else None,
    ]
    body = body or {}
    body_order = (
        "skin_tone",
        "height",
        "body_type",
        "breast_size",
        "chest",
        "waist",
        "hips",
        "butt_size",
        "muscle_tone",
        "body_hair",
    )
    for key in body_order:
        val = body.get(key)
        if not val:
            continue
        label = key.replace("_", " ")
        parts.append(f"{label}: {val}")
    # Any extra custom body keys
    for key, val in body.items():
        if key in body_order or not val:
            continue
        parts.append(f"{key.replace('_', ' ')}: {val}")

    if for_nsfw:
        parts.append("same consistent face and body")
    else:
        if style:
            parts.append(f"{style} fashion aesthetic")
        parts.append("consistent face and body identity")
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
    """Expand a short user / preset prompt into a richer generation prompt.

    Scene/framing/pose should already be in user_prompt from the UI presets.
    Do not force headshot/"portrait" framing — that blocked full-body gens.
    """
    _ = provider, system_prompt
    scene = user_prompt.strip() or "full body standing pose, studio lighting"

    if is_nsfw:
        nude_extra = ""
        if not prompt_implies_nsfw(scene):
            nude_extra = "nude, bare skin, "
        return (
            f"{scene}, {nude_extra}{influencer_name}, {looks_prompt}, "
            f"photorealistic adult photograph, natural skin texture, "
            f"sharp focus, detailed anatomy, entire subject visible in frame"
        )

    wardrobe = f", wearing {wardrobe_keywords}" if wardrobe_keywords else ""
    return (
        f"{scene}, {influencer_name}, {looks_prompt}{wardrobe}, "
        f"photorealistic, sharp focus, social media quality, entire subject visible in frame"
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
