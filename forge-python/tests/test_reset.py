from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from forge_python.config import Settings
from forge_python.reset import reset_app_data


def test_reset_wipes_db_and_media(tmp_path: Path) -> None:
    s = Settings()
    s.data_dir = tmp_path
    s.db_path = tmp_path / "data.db"
    s.media_dir = tmp_path / "media"
    s.generations_dir = s.media_dir / "generations"
    s.thumbnails_dir = s.media_dir / "thumbnails"
    s.models_dir = tmp_path / "models"
    s.vault_dir = tmp_path / "vault"
    s.uploads_dir = tmp_path / "uploads"
    s.ensure_directories()

    s.db_path.write_text("sqlite-junk", encoding="utf-8")
    Image.new("RGB", (8, 8), (1, 2, 3)).save(s.generations_dir / "1.png")
    (s.uploads_dir / "face.png").write_bytes(b"x")
    (s.vault_dir / "secret.bin").write_bytes(b"enc")
    keep = s.models_dir / "keep.bin"
    keep.write_bytes(b"model")

    report = reset_app_data(s, include_app_models=False)
    assert not s.db_path.exists()
    assert list(s.generations_dir.iterdir()) == []
    assert list(s.uploads_dir.iterdir()) == []
    assert list(s.vault_dir.iterdir()) == []
    assert keep.exists()
    assert report["removed"]["models"] == "kept"

    reset_app_data(s, include_app_models=True)
    # ensure_directories recreates models/llm/ (empty); no leftover weight files.
    leftover_files = [p for p in s.models_dir.rglob("*") if p.is_file()]
    assert leftover_files == []


@pytest.mark.asyncio
async def test_system_reset_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    Image.new("RGB", (4, 4), (9, 9, 9)).save(config.settings.generations_dir / "1.png")

    import forge_python.orchestrator as orch
    from forge_python.queue_worker import QueueWorker
    from forge_python.scheduler import ScheduleService
    from forge_python.vault import VaultService

    await orch.db.close()
    orch.db.db_path = config.settings.db_path
    await orch.db.connect()
    orch.vault = VaultService(orch.db)
    orch.queue = QueueWorker(orch.db, vault=orch.vault)
    orch.schedules = ScheduleService(orch.db)
    await orch.queue.start()
    orch.schedules.start()

    transport = ASGITransport(app=orch.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bad = await client.post("/api/system/reset", json={"confirm": "nope"})
        assert bad.status_code == 400
        ok = await client.post("/api/system/reset", json={"confirm": "RESET"})
        assert ok.status_code == 200
        body = ok.json()
        assert body["status"] == "reset"
        listed = await client.get("/api/influencers")
        assert listed.status_code == 200
        assert listed.json() == []

    assert not (config.settings.generations_dir / "1.png").exists()
    await orch.queue.stop()
    orch.schedules.shutdown()
    await orch.db.close()
    orch.queue = None
    orch.schedules = None
    orch.vault = None
