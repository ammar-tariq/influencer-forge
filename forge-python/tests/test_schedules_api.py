from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IFORGE_DATA_DIR", str(tmp_path))
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
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await orch.queue.stop()
    orch.schedules.shutdown()
    await orch.db.close()
    orch.queue = None
    orch.schedules = None
    orch.vault = None


async def _influencer(client: AsyncClient) -> int:
    p = await client.post(
        "/api/personalities",
        json={
            "name": "Sched",
            "bio": "b",
            "traits": {},
            "niche": "Lifestyle",
            "age_rating": "Adult",
        },
    )
    assert p.status_code == 200
    l = await client.post(
        "/api/looks",
        json={
            "name": "Look",
            "age": 22,
            "gender": "Female",
            "ethnicity": "Caucasian",
            "hair_color": "Brown",
            "hair_style": "Long",
            "eye_color": "Brown",
            "style": "Casual",
            "body": {},
        },
    )
    assert l.status_code == 200
    inf = await client.post(
        "/api/influencers",
        json={"personality_id": p.json()["id"], "looks_id": l.json()["id"], "name": "Sched"},
    )
    assert inf.status_code == 200
    return int(inf.json()["id"])


@pytest.mark.asyncio
async def test_schedule_create_patch_delete(client: AsyncClient) -> None:
    iid = await _influencer(client)
    created = await client.post(
        "/api/schedules",
        json={
            "influencer_id": iid,
            "schedule_time": "09:00:00",
            "frequency": "daily",
            "prompt_template": "morning coffee outdoors",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["next_trigger"]
    sid = body["id"]

    paused = await client.patch(f"/api/schedules/{sid}", json={"is_active": False})
    assert paused.status_code == 200
    assert paused.json()["is_active"] is False

    deleted = await client.delete(f"/api/schedules/{sid}")
    assert deleted.status_code == 200
    listed = await client.get("/api/schedules")
    assert all(s["id"] != sid for s in listed.json())
