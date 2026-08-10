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

# Partial clothing the model should keep (do not also force "nude").
_REVEALING_OUTFIT_HINTS = (
    "bikini",
    "swimsuit",
    "swimwear",
    "lingerie",
    "bra and panties",
    "underwear",
    "micro bikini",
    "thong",
    "sheer",
    "see-through",
)

_GENDER_PHRASE = {
    "female": "woman",
    "male": "man",
    "trans girl": "trans woman, feminine presentation",
}

_QUALITY_NEGATIVE = (
    "blurry, low quality, deformed, bad anatomy, extra limbs, watermark, text, logo, "
    "cartoon, anime, illustration, painting, cgi, 3d render, plastic skin, "
    "overprocessed, oversharpened, waxy skin, graphic novel"
)

SFW_NEGATIVE = (
    f"{_QUALITY_NEGATIVE}, "
    "cropped head only, extreme close-up face only"
)

# Fully unclothed asks — push away everyday clothes (keep list short to avoid mush).
NSFW_NUDE_NEGATIVE = (
    f"{_QUALITY_NEGATIVE}, "
    "shirt, blouse, jeans, jacket, hoodie, sweater, dress, coat, fully clothed streetwear"
)

# Bikini / lingerie asks — ban street clothes, not the outfit itself.
NSFW_OUTFIT_NEGATIVE = (
    f"{_QUALITY_NEGATIVE}, "
    "jeans, pants, shirt, blouse, hoodie, sweater, jacket, coat, office clothes"
)

_IDENTITY_LOCK = (
    "same person as reference photo, identical face, same facial features, "
    "same eye color, same nose and lips, same hair color and hairstyle"
)

# Backward-compatible alias used by older tests/docs.
NSFW_NEGATIVE = NSFW_NUDE_NEGATIVE


def prompt_implies_nsfw(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _EXPLICIT_HINTS) or any(
        hint in lowered for hint in _REVEALING_OUTFIT_HINTS
    )


def prompt_requests_revealing_outfit(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _REVEALING_OUTFIT_HINTS)


def prompt_requests_full_nude(text: str) -> bool:
    lowered = text.lower()
    nude_tokens = (
        "nude",
        "naked",
        "fully nude",
        "no clothes",
        "without clothes",
        "undressed",
        "topless",
        "bottomless",
        "bare breasts",
        "bare chest",
    )
    return any(token in lowered for token in nude_tokens)


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


def resolve_face_lock_path(looks: dict[str, Any] | None) -> str | None:
    """Prefer explicit Lock-this-face portrait, then Face Seed upload."""
    from pathlib import Path

    if not looks:
        return None
    for key in ("base_portrait_path", "reference_image_path"):
        candidate = looks.get(key)
        if candidate and Path(str(candidate)).is_file():
            return str(candidate)
    return None


def build_looks_prompt(
    *,
    age: int | None,
    ethnicity: str | None,
    hair_color: str | None,
    hair_style: str | None,
    eye_color: str | None,
    style: str | None,
    gender: str | None = None,
    nationality: str | None = None,
    body: dict[str, str] | None = None,
    for_nsfw: bool = False,
    face_locked: bool = False,
) -> str:
    """Build looks tokens for the prompt.

    When face_locked, omit hair/eyes/style text — the reference image is the source
    of truth. Wizard fields like \"Red Bob\" otherwise fight a curly lock photo.
    Nationality stays even when locked so body/scene cues (e.g. Russian, Chinese) remain.
    """
    person = gender_phrase(gender)
    nationality_token = None
    if nationality and str(nationality).strip():
        nat = str(nationality).strip()
        nationality_token = f"{nat} nationality" if "nationality" not in nat.lower() else nat
    parts: list[str | None] = [
        f"{age}-year-old adult {person}" if age else f"adult {person}",
        nationality_token,
        ethnicity,
    ]
    if not face_locked:
        parts.append(f"{hair_color} {hair_style} hair" if hair_color or hair_style else None)
        parts.append(f"{eye_color} eyes" if eye_color else None)

    body = body or {}
    if face_locked:
        # Shape only — skip noisy tags (body_hair, long muscle essays) that mush quality.
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
        )
    else:
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
        # Skip "Not applicable" style placeholders
        if str(val).strip().lower() in {"not applicable", "n/a", "none", "-"}:
            continue
        label = key.replace("_", " ")
        parts.append(f"{label}: {val}")
    if not face_locked:
        for key, val in body.items():
            if key in body_order or not val:
                continue
            parts.append(f"{key.replace('_', ' ')}: {val}")

    if face_locked:
        return ", ".join(p for p in parts if p)

    if for_nsfw:
        parts.append("same consistent face and body")
    else:
        if style:
            parts.append(f"{style} fashion aesthetic")
        parts.append("consistent face and body identity")
    return ", ".join(p for p in parts if p)


def _compact_scene(scene: str, *, max_chars: int = 220) -> str:
    """Keep user scene short — long stacked presets turn RealVisXL graphic/mushy."""
    cleaned = re.sub(r"\s+", " ", scene).strip(" ,")
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rsplit(" ", 1)[0] + "…"


def expand_prompt(
    user_prompt: str,
    *,
    influencer_name: str,
    looks_prompt: str,
    wardrobe_keywords: str | None = None,
    system_prompt: str | None = None,
    provider: str = "template",
    is_nsfw: bool = False,
    face_locked: bool = False,
) -> str:
    """Expand a short user / preset prompt into a richer generation prompt.

    Scene/framing/pose should already be in user_prompt from the UI presets.
    When face_locked, lead with identity tokens and keep the prompt shorter so
    img2img does not drift hair/face or go overcooked/graphic.
    """
    _ = provider, system_prompt
    scene = _compact_scene(user_prompt.strip() or "full body standing pose, studio lighting")
    identity = f"{_IDENTITY_LOCK}, {influencer_name}, {looks_prompt}" if face_locked else f"{influencer_name}, {looks_prompt}"
    quality = "photorealistic photograph, natural skin texture, sharp focus"

    if is_nsfw:
        outfit = prompt_requests_revealing_outfit(scene)
        wants_nude = prompt_requests_full_nude(scene)
        extra = ""
        if not outfit and not wants_nude:
            extra = "nude, bare skin, "
        elif outfit and not wants_nude:
            extra = "skin visible, "
        # Identity first when locked — CLIP attends strongest to early tokens.
        if face_locked:
            return f"{identity}, {scene}, {extra}{quality}"
        return f"{scene}, {extra}{identity}, {quality}"

    wardrobe = f", wearing {wardrobe_keywords}" if wardrobe_keywords else ""
    if face_locked:
        return f"{identity}, {scene}{wardrobe}, {quality}"
    return f"{scene}, {identity}{wardrobe}, {quality}"


def resolve_negative_prompt(
    *,
    is_nsfw: bool,
    custom: str | None = None,
    user_prompt: str | None = None,
) -> str:
    if custom and custom.strip():
        return custom.strip()
    if not is_nsfw:
        return SFW_NEGATIVE
    scene = user_prompt or ""
    if prompt_requests_revealing_outfit(scene) and not prompt_requests_full_nude(scene):
        return NSFW_OUTFIT_NEGATIVE
    return NSFW_NUDE_NEGATIVE


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
