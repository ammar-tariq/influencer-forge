"""Privacy vault: Argon2id PIN + AES-256-GCM file encryption."""

from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from PIL import Image, ImageFilter

from forge_python.config import settings
from forge_python.db import Database

ph = PasswordHasher()


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

    async def unlock(self, pin: str) -> bool:
        row = await self.db.fetchone("SELECT * FROM vault_metadata WHERE id = 1")
        if not row:
            return False
        try:
            ph.verify(row["pin_hash"], pin)
        except VerifyMismatchError:
            return False
        self._unlocked_key = self._derive_key(pin, row["pin_salt"])
        return True

    def lock(self) -> None:
        self._unlocked_key = None

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
        dest.write_bytes(nonce + encrypted)

    def decrypt_file(self, source: Path, dest: Path) -> None:
        if self._unlocked_key is None:
            raise RuntimeError("Vault is locked")
        blob = source.read_bytes()
        nonce, encrypted = blob[:12], blob[12:]
        aes = AESGCM(self._unlocked_key)
        dest.write_bytes(aes.decrypt(nonce, encrypted, None))

    def make_teaser(self, source: Path, dest: Path) -> None:
        image = Image.open(source).convert("RGBA")
        blurred = image.filter(ImageFilter.GaussianBlur(radius=18))
        blurred.save(dest)

    async def vault_generation(self, generation_id: int) -> dict[str, str]:
        if self._unlocked_key is None:
            raise RuntimeError("Vault is locked")
        row = await self.db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
        if not row or not row["output_path"]:
            raise ValueError("Generation output missing")
        source = Path(row["output_path"])
        vault_path = settings.vault_dir / f"{generation_id}.bin"
        teaser = settings.thumbnails_dir / f"{generation_id}_teaser.png"
        self.encrypt_file(source, vault_path)
        self.make_teaser(source, teaser)
        await self.db.execute(
            """
            UPDATE generations
            SET is_vaulted = 1, vault_file_path = ?, teaser_path = ?
            WHERE id = ?
            """,
            (str(vault_path), str(teaser), generation_id),
        )
        return {"vault_file_path": str(vault_path), "teaser_path": str(teaser)}

    @staticmethod
    def encode_key_marker(key: bytes) -> str:
        return base64.b64encode(key).decode("ascii")
