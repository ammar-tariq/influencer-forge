import pytest

from forge_python.config import Settings
from forge_python.db import Database


@pytest.fixture
async def database(tmp_path):
    settings = Settings()
    settings.data_dir = tmp_path
    settings.db_path = tmp_path / "data.db"
    settings.media_dir = tmp_path / "media"
    settings.generations_dir = settings.media_dir / "generations"
    settings.thumbnails_dir = settings.media_dir / "thumbnails"
    settings.models_dir = tmp_path / "models"
    settings.vault_dir = tmp_path / "vault"
    settings.uploads_dir = tmp_path / "uploads"
    settings.ensure_directories()
    db = Database(settings.db_path)
    await db.connect()
    yield db
    await db.close()


@pytest.mark.asyncio
async def test_schema_and_settings(database: Database) -> None:
    await database.set_setting("llm_provider", "local")
    assert await database.get_setting("llm_provider") == "local"
    rows = await database.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    names = {r["name"] for r in rows}
    assert "personalities" in names
    assert "generations" in names
    assert "vault_metadata" in names
