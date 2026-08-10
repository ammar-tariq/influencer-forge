import pytest
from httpx import ASGITransport, AsyncClient
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
    s.uploads_dir = s.media_dir / "uploads"
    s.legacy_uploads_dir = tmp_path / "uploads"
    s.models_dir = tmp_path / "models"
    s.ensure_directories()
    monkeypatch.setattr("forge_python.vault.settings", s)
    db = Database(s.db_path)
    await db.connect()
    yield db, s
    await db.close()


async def _seed_generation(db: Database, s: Settings, *, gid: int = 1, nsfw: int = 1) -> None:
    await db.execute(
        """
        INSERT INTO personalities(name, bio, traits, niche, age_rating, system_prompt)
        VALUES('Natasha', '', '{}', 'Adult', '18+', 'sys')
        """
    )
    await db.execute(
        """
        INSERT INTO looks(name, age, ethnicity, hair_color, hair_style, eye_color, style, base_prompt)
        VALUES('Look', 20, 'Caucasian', 'Brown', 'Long', 'Brown', 'Glam', 'look')
        """
    )
    await db.execute(
        "INSERT INTO influencers(personality_id, looks_id, name) VALUES(1, 1, 'Natasha')"
    )
    src = s.generations_dir / f"{gid}.png"
    thumb = s.thumbnails_dir / f"{gid}_thumb.png"
    Image.new("RGB", (64, 64), (200, 40, 80)).save(src)
    Image.new("RGB", (32, 32), (200, 40, 80)).save(thumb)
    await db.execute(
        """
        INSERT INTO generations(
            id, influencer_id, user_prompt, expanded_prompt, workflow_type, model_used, llm_used,
            aspect_ratio, output_path, output_thumbnail_path, is_nsfw, status
        ) VALUES(?, 1, 'Topless', 'Topless expanded', 'image', 'sdxl', 'template',
                 '9:16', ?, ?, ?, 'completed')
        """,
        (gid, str(src), str(thumb), nsfw),
    )


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


@pytest.mark.asyncio
async def test_vault_generation_wipes_cleartext(vault_env) -> None:
    db, s = vault_env
    await _seed_generation(db, s, gid=7)
    vault = VaultService(db)
    await vault.setup("4321")
    src = s.generations_dir / "7.png"
    thumb = s.thumbnails_dir / "7_thumb.png"
    assert src.exists() and thumb.exists()

    result = await vault.vault_generation(7)
    assert "teaser_path" in result
    assert not src.exists()
    assert not thumb.exists()
    teaser = s.thumbnails_dir / "7_teaser.png"
    assert teaser.exists()
    assert (s.vault_dir / "7.bin").exists()

    row = await db.fetchone("SELECT * FROM generations WHERE id = 7")
    assert row["is_vaulted"] == 1
    assert row["output_path"] is None
    assert row["output_thumbnail_path"] is None
    assert row["teaser_path"]


@pytest.mark.asyncio
async def test_vault_pending_and_reveal(vault_env) -> None:
    db, s = vault_env
    await _seed_generation(db, s, gid=3)
    vault = VaultService(db)
    await vault.setup("9999")
    assert await vault.count_pending_nsfw() == 1
    pending = await vault.vault_pending_nsfw()
    assert pending["count"] == 1
    assert pending["vaulted"] == [3]
    assert await vault.count_pending_nsfw() == 0

    revealed = await vault.reveal_generation(3)
    assert revealed.exists()
    vault.lock()
    with pytest.raises(RuntimeError, match="locked"):
        await vault.reveal_generation(3)


@pytest.mark.asyncio
async def test_vault_reveal_api_requires_unlock(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IFORGE_DATA_DIR", str(tmp_path))
    from forge_python import config

    config.settings.data_dir = tmp_path
    config.settings.db_path = tmp_path / "data.db"
    config.settings.media_dir = tmp_path / "media"
    config.settings.generations_dir = config.settings.media_dir / "generations"
    config.settings.thumbnails_dir = config.settings.media_dir / "thumbnails"
    config.settings.uploads_dir = config.settings.media_dir / "uploads"
    config.settings.legacy_uploads_dir = tmp_path / "uploads"
    config.settings.vault_dir = tmp_path / "vault"
    config.settings.models_dir = tmp_path / "models"
    config.settings.ensure_directories()
    monkeypatch.setattr("forge_python.vault.settings", config.settings)

    from forge_python.orchestrator import app, db, vault

    await db.close()
    db.db_path = config.settings.db_path
    await db.connect()
    # Rebind module vault used by routes
    import forge_python.orchestrator as orch

    orch.vault = VaultService(db)
    await _seed_generation(db, config.settings, gid=11)
    await orch.vault.setup("5555")
    await orch.vault.vault_generation(11)
    orch.vault.lock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        locked = await client.get("/api/vault/generations/11/image")
        assert locked.status_code == 401
        await client.post("/api/vault/unlock", json={"pin": "5555"})
        ok = await client.get("/api/vault/generations/11/image")
        assert ok.status_code == 200
        assert ok.headers["content-type"].startswith("image/")
        listed = await client.get("/api/vault/generations")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

    await db.close()
