"""Authoritative clothing / scene resolution for generation prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass

from forge_python.llm_manager import (
    prompt_implies_nsfw,
    prompt_requests_full_nude,
    prompt_requests_revealing_outfit,
)

# Tokens stripped from free-form notes / scene when wardrobe owns clothing.
# Do not span commas — "wearing X, soft smile" must keep the smile clause.
_CLOTHING_NOTE_PATTERNS = (
    r"\bwearing\b[^,]{0,48}",
    r"\bdressed in\b[^,]{0,48}",
    r"\boutfit\b",
    r"\bclothes?\b",
    r"\bclothing\b",
    r"\bdress(?:es)?\b",
    r"\bskirt\b",
    r"\bjeans\b",
    r"\bpants\b",
    r"\btrousers\b",
    r"\bshorts\b",
    r"\bshirt\b",
    r"\bblouse\b",
    r"\bhoodie\b",
    r"\bsweater\b",
    r"\bjacket\b",
    r"\bcoat\b",
    r"\btop\b",
    r"\bgown\b",
    r"\bsuit\b",
    r"\buniform\b",
    r"\bathleisure\b",
    r"\bstreetwear\b",
    r"\bbikini\b",
    r"\bswimsuit\b",
    r"\bswimwear\b",
    r"\blingerie\b",
    r"\bbra\b",
    r"\bpanties\b",
    r"\bunderwear\b",
    r"\bthong\b",
    r"\bnude\b",
    r"\bnaked\b",
    r"\btopless\b",
    r"\bbottomless\b",
    r"\bundressed\b",
    r"\bno clothes\b",
    r"\bwithout clothes\b",
    r"\bfully nude\b",
    r"\bbare breasts\b",
    r"\bbare chest\b",
)

_CLOTHING_RE = re.compile("|".join(_CLOTHING_NOTE_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class ResolvedPromptLayers:
    """Layers after wardrobe / dressing / notes resolution."""

    scene: str
    wardrobe_keywords: str | None
    is_nsfw: bool
    clothing_from_wardrobe: bool


class ClothingConflictError(ValueError):
    """Wardrobe cannot combine with nude / topless scene language."""


def strip_clothing_from_text(text: str) -> str:
    """Remove clothing / nude tokens so notes stay vibe-only when wardrobe wins."""
    if not text:
        return ""
    cleaned = _CLOTHING_RE.sub(" ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s*,\s*,+", ", ", cleaned)
    return cleaned.strip(" ,")


def wardrobe_conflicts_with_nude(user_prompt: str, *, wardrobe_keywords: str | None) -> bool:
    if not wardrobe_keywords or not wardrobe_keywords.strip():
        return False
    return prompt_requests_full_nude(user_prompt)


def resolve_prompt_layers(
    user_prompt: str,
    *,
    wardrobe_keywords: str | None = None,
    is_nsfw_flag: bool = False,
) -> ResolvedPromptLayers:
    """Apply clothing override contract.

    Priority: wardrobe (if set) > dressing/scene clothing already in user_prompt.
    When wardrobe is set, clothing words in the prompt/notes are stripped.
    Wardrobe + nude/topless language is rejected.
    """
    raw = (user_prompt or "").strip()
    has_wardrobe = bool(wardrobe_keywords and wardrobe_keywords.strip())

    if has_wardrobe and wardrobe_conflicts_with_nude(raw, wardrobe_keywords=wardrobe_keywords):
        raise ClothingConflictError(
            "Wardrobe cannot be combined with nude/topless. Clear wardrobe or pick a clothed scene."
        )

    if has_wardrobe:
        scene = strip_clothing_from_text(raw) or "full body standing pose, studio lighting"
        # NSFW only from wardrobe keywords / explicit flag — not from stripped notes.
        is_nsfw = bool(
            is_nsfw_flag
            or prompt_implies_nsfw(wardrobe_keywords or "")
            or prompt_requests_revealing_outfit(wardrobe_keywords or "")
        )
        return ResolvedPromptLayers(
            scene=scene,
            wardrobe_keywords=wardrobe_keywords.strip() if wardrobe_keywords else None,
            is_nsfw=is_nsfw,
            clothing_from_wardrobe=True,
        )

    is_nsfw = bool(is_nsfw_flag or prompt_implies_nsfw(raw))
    return ResolvedPromptLayers(
        scene=raw or "full body standing pose, studio lighting",
        wardrobe_keywords=None,
        is_nsfw=is_nsfw,
        clothing_from_wardrobe=False,
    )
