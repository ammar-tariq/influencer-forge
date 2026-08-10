import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IFORGE_DATA_DIR", str(tmp_path))
    # Re-import settings-bound modules with temp data dir
    from forge_python import config

    config.settings.data_dir = tmp_path
    config.settings.db_path = tmp_path / "data.db"
    config.settings.media_dir = tmp_path / "media"
    config.settings.generations_dir = config.settings.media_dir / "generations"
    config.settings.thumbnails_dir = config.settings.media_dir / "thumbnails"
    config.settings.models_dir = tmp_path / "models"
    config.settings.vault_dir = tmp_path / "vault"
    config.settings.uploads_dir = config.settings.media_dir / "uploads"
    config.settings.legacy_uploads_dir = tmp_path / "uploads"
    config.settings.ensure_directories()

    from forge_python.orchestrator import app, db

    await db.close()
    db.db_path = config.settings.db_path
    await db.connect()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await db.close()


@pytest.mark.asyncio
async def test_health_and_bootstrap(client: AsyncClient) -> None:
    health = await client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert "InfluencerForge" in body["data_dir"] or os.environ["IFORGE_DATA_DIR"] in body["data_dir"]

    boot = await client.get("/api/bootstrap/status")
    assert boot.status_code == 200
