"""Privacy vault: Argon2id PIN + AES-256-GCM file encryption."""

from __future__ import annotations

import base64
import logging
import os
import secrets
import shutil
from pathlib import Path
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from PIL import Image, ImageFilter

from forge_python.config import settings
from forge_python.db import Database

ph = PasswordHasher()
logger = logging.getLogger(__name__)


class VaultService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._unlocked_key: bytes | None = None

    async def is_configured(self) -> bool:
        row = await self.db.fetchone("SELECT id FROM vault_metadata WHERE id = 1")
        return row is not None

    async def setup(self, pin: str) -> None:
        settings.ensure_directories()
        salt = secrets.token_hex(16)
        pin_hash = ph.hash(pin)
        await self.db.execute(
            """
            INSERT INTO vault_metadata(id, pin_hash, pin_salt, vault_path)
            VALUES(1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET pin_hash = excluded.pin_hash,
              pin_salt = excluded.pin_salt, vault_path = excluded.vault_path
            """,
            (pin_hash, salt, str(settings.vault_dir)),
        )
        self._unlocked_key = self._derive_key(pin, salt)
        await self._auto_vault_pending_safe()

    async def _auto_vault_pending_safe(self) -> None:
        try:
            pending = await self.vault_pending_nsfw()
            if pending.get("count"):
                logger.info("Auto-vaulted %s pending NSFW", pending["count"])
        except (RuntimeError, ValueError, OSError) as exc:
            logger.warning("Auto-vault pending failed: %s", exc)

    async def unlock(self, pin: str) -> bool:
        row = await self.db.fetchone("SELECT * FROM vault_metadata WHERE id = 1")
        if not row:
            return False
        try:
            ph.verify(row["pin_hash"], pin)
        except VerifyMismatchError:
            return False
        self._unlocked_key = self._derive_key(pin, row["pin_salt"])
        # Any pending cleartext NSFW is encrypted as soon as the vault can open.
        await self._auto_vault_pending_safe()
        return True

    def lock(self) -> None:
        self._unlocked_key = None
        self._wipe_reveal_cache()

    @property
    def unlocked(self) -> bool:
        return self._unlocked_key is not None

    def _derive_key(self, pin: str, salt_hex: str) -> bytes:
        salt = bytes.fromhex(salt_hex)
        return HKDF(algorithm=SHA256(), length=32, salt=salt, info=b"influencerforge-vault").derive(
            pin.encode("utf-8")
        )

    def encrypt_file(self, source: Path, dest: Path) -> None:
        if self._unlocked_key is None:
            raise RuntimeError("Vault is locked")
        data = source.read_bytes()
        nonce = os.urandom(12)
        aes = AESGCM(self._unlocked_key)
        encrypted = aes.encrypt(nonce, data, None)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(nonce + encrypted)

    def decrypt_file(self, source: Path, dest: Path) -> None:
        if self._unlocked_key is None:
            raise RuntimeError("Vault is locked")
        blob = source.read_bytes()
        nonce, encrypted = blob[:12], blob[12:]
        aes = AESGCM(self._unlocked_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(aes.decrypt(nonce, encrypted, None))

    def make_teaser(self, source: Path, dest: Path) -> None:
        image = Image.open(source).convert("RGBA")
        blurred = image.filter(ImageFilter.GaussianBlur(radius=18))
        dest.parent.mkdir(parents=True, exist_ok=True)
        blurred.save(dest)

    def reveal_cache_dir(self) -> Path:
        path = settings.media_dir / "vault_cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _wipe_reveal_cache(self) -> None:
        cache = settings.media_dir / "vault_cache"
        if cache.exists():
            shutil.rmtree(cache, ignore_errors=True)

    def end_view_session(self) -> None:
        """Wipe decrypted reveal cache but keep the vault unlocked for browsing teasers."""
        self._wipe_reveal_cache()

    async def vault_generation(self, generation_id: int) -> dict[str, str]:
        """Encrypt output, write teaser, wipe cleartext paths from disk + DB."""
        if self._unlocked_key is None:
            raise RuntimeError("Vault is locked")
        row = await self.db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
        if not row:
            raise ValueError("Generation not found")
        if row.get("is_vaulted") and row.get("vault_file_path"):
            return {
                "vault_file_path": str(row["vault_file_path"]),
                "teaser_path": str(row.get("teaser_path") or ""),
            }
        if not row.get("output_path"):
            raise ValueError("Generation output missing")
        source = Path(row["output_path"])
        if not source.is_file():
            raise ValueError("Generation output file missing on disk")

        settings.ensure_directories()
        vault_path = settings.vault_dir / f"{generation_id}.bin"
        teaser = settings.thumbnails_dir / f"{generation_id}_teaser.png"
        self.encrypt_file(source, vault_path)
        self.make_teaser(source, teaser)

        thumb = row.get("output_thumbnail_path")
        await self.db.execute(
            """
            UPDATE generations
            SET is_vaulted = 1,
                vault_file_path = ?,
                teaser_path = ?,
                output_path = NULL,
                output_thumbnail_path = NULL
            WHERE id = ?
            """,
            (str(vault_path), str(teaser), generation_id),
        )
        source.unlink(missing_ok=True)
        if thumb:
            Path(str(thumb)).unlink(missing_ok=True)

        return {"vault_file_path": str(vault_path), "teaser_path": str(teaser)}

    async def list_vaulted(self) -> list[dict[str, Any]]:
        rows = await self.db.fetchall(
            """
            SELECT id, influencer_id, user_prompt, teaser_path, vault_file_path,
                   created_at, completed_at, is_nsfw
            FROM generations
            WHERE is_vaulted = 1
            ORDER BY id DESC
            """
        )
        return [dict(r) for r in rows]

    async def count_pending_nsfw(self) -> int:
        row = await self.db.fetchone(
            """
            SELECT COUNT(*) AS c FROM generations
            WHERE is_nsfw = 1 AND COALESCE(is_vaulted, 0) = 0
              AND status = 'completed' AND output_path IS NOT NULL
            """
        )
        return int((row or {}).get("c") or 0)

    async def vault_pending_nsfw(self) -> dict[str, Any]:
        if self._unlocked_key is None:
            raise RuntimeError("Vault is locked")
        rows = await self.db.fetchall(
            """
            SELECT id FROM generations
            WHERE is_nsfw = 1 AND COALESCE(is_vaulted, 0) = 0
              AND status = 'completed' AND output_path IS NOT NULL
            ORDER BY id
            """
        )
        vaulted: list[int] = []
        errors: list[dict[str, str]] = []
        for row in rows:
            gid = int(row["id"])
            try:
                await self.vault_generation(gid)
                vaulted.append(gid)
            except (RuntimeError, ValueError, OSError) as exc:
                logger.warning("Failed to vault generation %s: %s", gid, exc)
                errors.append({"id": str(gid), "error": str(exc)})
        return {"vaulted": vaulted, "errors": errors, "count": len(vaulted)}

    async def reveal_generation(self, generation_id: int) -> Path:
        """Decrypt vaulted image into a short-lived cache file for FileResponse."""
        if self._unlocked_key is None:
            raise RuntimeError("Vault is locked")
        row = await self.db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
        if not row or not row.get("is_vaulted") or not row.get("vault_file_path"):
            raise ValueError("Vaulted generation not found")
        vault_path = Path(str(row["vault_file_path"]))
        if not vault_path.is_file():
            raise ValueError("Vault file missing on disk")
        dest = self.reveal_cache_dir() / f"{generation_id}.png"
        self.decrypt_file(vault_path, dest)
        return dest

    @staticmethod
    def encode_key_marker(key: bytes) -> str:
        return base64.b64encode(key).decode("ascii")
