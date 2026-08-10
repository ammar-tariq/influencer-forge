import pytest
from PIL import Image

from forge_python.config import Settings
from forge_python.db import Database
from forge_python.vault import VaultService


@pytest.fixture
async def vault_env(tmp_path, monkeypatch):
    s = Settings()
    s.data_dir = tmp_path
    s.db_path = tmp_path / "data.db"
    s.media_dir = tmp_path / "media"
    s.generations_dir = s.media_dir / "generations"
    s.thumbnails_dir = s.media_dir / "thumbnails"
    s.vault_dir = tmp_path / "vault"
    s.uploads_dir = tmp_path / "uploads"
    s.models_dir = tmp_path / "models"
    s.ensure_directories()
    monkeypatch.setattr("forge_python.vault.settings", s)
    db = Database(s.db_path)
    await db.connect()
    yield db, s
    await db.close()


@pytest.mark.asyncio
async def test_vault_pin_and_encrypt(vault_env) -> None:
    db, s = vault_env
    vault = VaultService(db)
    await vault.setup("1234")
    assert await vault.unlock("9999") is False
    assert await vault.unlock("1234") is True
    src = s.generations_dir / "sample.png"
    Image.new("RGB", (64, 64), (10, 20, 30)).save(src)
    dest = s.vault_dir / "sample.bin"
    vault.encrypt_file(src, dest)
    assert dest.exists()
    restored = s.generations_dir / "restored.png"
    vault.decrypt_file(dest, restored)
    assert restored.exists()
