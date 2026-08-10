"""Face Seed helpers.

Phase 2 stores a deterministic local fingerprint from the reference image so
Looks rows can track face consistency before InstantID/IP-Adapter embeddings
are available. When ComfyUI InstantID is wired, replace `extract_face_embedding`
with the real embedding tensor bytes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


def extract_face_embedding(image_path: Path) -> bytes:
    """Return a stable fingerprint blob derived from a normalized face crop proxy."""
    with Image.open(image_path) as img:
        rgb = img.convert("RGB").resize((128, 128))
        payload = rgb.tobytes()
    digest = hashlib.sha256(payload).digest()
    # 512-byte placeholder vector (repeat digest) — swap for InstantID later.
    return (digest * 16)[:512]


def embedding_present(blob: bytes | None) -> bool:
    return bool(blob) and len(blob) > 0
