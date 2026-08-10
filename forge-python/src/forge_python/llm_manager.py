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

# Adult silhouette fields that fight age-accurate under-18 bodies.
_ADULT_BODY_KEYS = frozenset({"breast_size", "butt_size", "waist", "hips"})

# Body-type labels that imply mature curves — remap under 18.
_YOUTH_BODY_TYPE_MAP = {
    "curvy": "slim youthful build",
    "hourglass": "slim youthful build",
    "pear": "slim youthful build",
    "apple": "soft youthful midsection",
    "plus-size": "soft youthful build",
    "soft / plump": "soft youthful build",
    "muscular": "lightly athletic youth",
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


def gender_phrase(gender: str | None, age: int | None = None) -> str:
    """Person noun for prompts; under 18 uses girl/boy so SDXL does not default to adult."""
    if not gender:
        base_key = "female"
    else:
        base_key = gender.strip().lower()
    adult = _GENDER_PHRASE.get(base_key, gender.strip() if gender else "person")
    if age is None or age >= 18:
        return adult
    if base_key in ("female", "trans girl"):
        return "girl" if age < 15 else "teenage girl"
    if base_key == "male":
        return "boy" if age < 15 else "teenage boy"
    return adult


def _normalize_youth_body(body: dict[str, str], age: int) -> dict[str, str]:
    """Drop / remap adult body tokens so height + age drive proportions."""
    out: dict[str, str] = {}
    for key, val in body.items():
        if not val:
            continue
        if key in _ADULT_BODY_KEYS:
            continue
        if key == "body_type":
            mapped = _YOUTH_BODY_TYPE_MAP.get(str(val).strip().lower())
            out[key] = mapped or f"{val}, youthful proportions"
            continue
        if key == "muscle_tone":
            lowered = str(val).strip().lower()
            if "very muscular" in lowered or "athletic definition" in lowered:
                out[key] = "lightly toned youthful"
                continue
        if key == "chest":
            lowered = str(val).strip().lower()
            if "broad" in lowered or "muscular" in lowered:
                out[key] = "slim youthful chest"
                continue
        out[key] = val
    return out


def _age_body_cues(age: int, height: str | None) -> list[str]:
    """Strong positive tokens so height stays but body matches stated age."""
    cues = [
        f"age-accurate {age}-year-old body proportions",
        "youthful frame matching stated age, not an adult body",
        "no mature curves",
    ]
    if height and str(height).strip():
        cues.append(
            f"height: {height.strip()}, true-to-age stature for a {age}-year-old "
            f"(same height band, child/teen proportions not adult)"
        )
    if age <= 14:
        cues.append("early adolescent proportions, still-growing physique")
    elif age <= 17:
        cues.append("teenage proportions, not fully adult silhouette")
    return cues


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

    Under 18: use girl/boy phrasing, keep height, drop adult breast/hip/butt tokens,
    and add explicit age-accurate proportion cues so SDXL does not invent an adult body.
    """
    person = gender_phrase(gender, age)
    nationality_token = None
    if nationality and str(nationality).strip():
        nat = str(nationality).strip()
        nationality_token = f"{nat} nationality" if "nationality" not in nat.lower() else nat
    if age is not None:
        age_token = f"{age}-year-old {person}"
    else:
        age_token = person
    parts: list[str | None] = [
        age_token,
        nationality_token,
        ethnicity,
    ]
    if not face_locked:
        parts.append(f"{hair_color} {hair_style} hair" if hair_color or hair_style else None)
        parts.append(f"{eye_color} eyes" if eye_color else None)

    raw_body = body or {}
    youth = age is not None and age < 18
    if youth:
        body = _normalize_youth_body(raw_body, age)
        # Height is stated in age cues — avoid duplicating a bare height line.
        for cue in _age_body_cues(age, raw_body.get("height")):
            parts.append(cue)
    else:
        body = dict(raw_body)

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
        if youth and key == "height":
            continue  # already in age/height cues
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
    clothing_from_wardrobe: bool = False,
) -> str:
    """Expand a short user / preset prompt into a richer generation prompt.

    Scene/framing/pose should already be in user_prompt from the UI presets.
    When face_locked, lead with identity tokens and keep the prompt shorter so
    img2img does not drift hair/face or go overcooked/graphic.

    Clothing: wardrobe keywords (if any) are the sole outfit source — never inject
    blanket ``nude`` when wardrobe or a revealing outfit is already specified.
    """
    _ = provider, system_prompt
    scene = _compact_scene(user_prompt.strip() or "full body standing pose, studio lighting")
    identity = (
        f"{_IDENTITY_LOCK}, {influencer_name}, {looks_prompt}"
        if face_locked
        else f"{influencer_name}, {looks_prompt}"
    )
    quality = "photorealistic photograph, natural skin texture, sharp focus"

    from_wardrobe = bool(clothing_from_wardrobe or (wardrobe_keywords and wardrobe_keywords.strip()))
    clothing_src = wardrobe_keywords if from_wardrobe and wardrobe_keywords else scene
    outfit = prompt_requests_revealing_outfit(clothing_src) or (
        bool(wardrobe_keywords) and prompt_requests_revealing_outfit(wardrobe_keywords)
    )
    wants_nude = (not from_wardrobe) and prompt_requests_full_nude(clothing_src)

    wardrobe_bit = ""
    if from_wardrobe and wardrobe_keywords:
        wardrobe_bit = f", wearing {wardrobe_keywords.strip()}"

    extra = ""
    if is_nsfw:
        if from_wardrobe or outfit:
            # Wardrobe / lingerie / bikini — do not override with nude.
            if outfit and not wants_nude:
                extra = "skin visible, "
        elif wants_nude:
            extra = "nude, bare skin, "
        else:
            # Explicit NSFW toggle without outfit language.
            extra = "nude, bare skin, "

    if face_locked:
        return f"{identity}, {scene}{wardrobe_bit}, {extra}{quality}".replace(", ,", ",")
    return f"{scene}{wardrobe_bit}, {identity}, {extra}{quality}".replace(", ,", ",")


_YOUTH_NEGATIVE = (
    "adult body, mature woman, mature man, voluptuous, exaggerated curves, "
    "large breasts, wide hips, heavy makeup, bodybuilder physique"
)


def resolve_negative_prompt(
    *,
    is_nsfw: bool,
    custom: str | None = None,
    user_prompt: str | None = None,
    wardrobe_keywords: str | None = None,
    clothing_from_wardrobe: bool = False,
    age: int | None = None,
) -> str:
    if custom and custom.strip():
        return custom.strip()
    if not is_nsfw:
        base = SFW_NEGATIVE
    else:
        from_wardrobe = bool(clothing_from_wardrobe or (wardrobe_keywords and wardrobe_keywords.strip()))
        clothing_src = (
            wardrobe_keywords
            if from_wardrobe and wardrobe_keywords
            else (user_prompt or "")
        )
        if from_wardrobe or (
            prompt_requests_revealing_outfit(clothing_src)
            and not prompt_requests_full_nude(clothing_src)
        ):
            base = NSFW_OUTFIT_NEGATIVE
        else:
            base = NSFW_NUDE_NEGATIVE
    if age is not None and age < 18:
        return f"{base}, {_YOUTH_NEGATIVE}"
    return base


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
