from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IFORGE_DATA_DIR", str(tmp_path))
    from forge_python import config

    config.settings.data_dir = tmp_path
    config.settings.db_path = tmp_path / "data.db"
    config.settings.media_dir = tmp_path / "media"
    config.settings.generations_dir = config.settings.media_dir / "generations"
    config.settings.thumbnails_dir = config.settings.media_dir / "thumbnails"
    config.settings.uploads_dir = config.settings.media_dir / "uploads"
    config.settings.legacy_uploads_dir = tmp_path / "uploads"
    config.settings.models_dir = tmp_path / "models"
    config.settings.vault_dir = tmp_path / "vault"
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
async def test_face_seed_served_under_media_and_avatar(client: AsyncClient, tmp_path: Path) -> None:
    from forge_python import config

    # Personality + looks
    p = await client.post(
        "/api/personalities",
        json={
            "name": "Ava",
            "bio": "",
            "niche": "Fashion",
            "age_rating": "Teen",
            "traits": {"tone": "Friendly"},
        },
    )
    assert p.status_code == 200
    pid = p.json()["id"]

    looks = await client.post(
        "/api/looks",
        json={"name": "Ava Look", "age": 24, "ethnicity": "Caucasian", "hair_color": "Brown"},
    )
    assert looks.status_code == 200
    lid = looks.json()["id"]

    seed = tmp_path / "seed.png"
    Image.new("RGB", (64, 64), color=(200, 100, 80)).save(seed)

    with seed.open("rb") as fh:
        up = await client.post(
            f"/api/looks/{lid}/face-seed",
            files={"file": ("seed.png", fh, "image/png")},
        )
    assert up.status_code == 200
    ref = up.json()["reference_image_path"]
    assert "/media/uploads/" in ref.replace("\\", "/") or ref.endswith("seed.png")
    assert Path(ref).exists()
    assert Path(ref).parent == config.settings.uploads_dir

    media_name = Path(ref).name
    served = await client.get(f"/media/uploads/{media_name}")
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/")

    inf = await client.post(
        "/api/influencers",
        json={"personality_id": pid, "looks_id": lid, "name": "Ava"},
    )
    assert inf.status_code == 200
    assert inf.json()["avatar_path"]
    assert "face_" in Path(inf.json()["avatar_path"]).name

    listed = await client.get("/api/influencers")
    assert listed.status_code == 200
    assert listed.json()[0]["avatar_path"]


def test_legacy_uploads_migrate_into_media(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IFORGE_DATA_DIR", str(tmp_path))
    from forge_python.config import Settings

    s = Settings()
    s.data_dir = tmp_path
    s.media_dir = tmp_path / "media"
    s.generations_dir = s.media_dir / "generations"
    s.thumbnails_dir = s.media_dir / "thumbnails"
    s.uploads_dir = s.media_dir / "uploads"
    s.legacy_uploads_dir = tmp_path / "uploads"
    s.models_dir = tmp_path / "models"
    s.vault_dir = tmp_path / "vault"

    legacy = s.legacy_uploads_dir
    legacy.mkdir(parents=True)
    old = legacy / "face_9_old.png"
    old.write_bytes(b"png")

    s.ensure_directories()
    assert (s.uploads_dir / "face_9_old.png").exists()
    assert not old.exists()
