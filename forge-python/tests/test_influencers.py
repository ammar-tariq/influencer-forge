"""Influencer list, detail, and archive API."""

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

    from forge_python.orchestrator import app, db

    await db.close()
    db.db_path = config.settings.db_path
    await db.connect()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await db.close()


async def _create_influencer(client: AsyncClient, name: str = "Natasha") -> int:
    personality = await client.post(
        "/api/personalities",
        json={
            "name": name,
            "bio": "Test bio",
            "traits": {"tone": "warm"},
            "niche": "Lifestyle",
            "age_rating": "Adult",
        },
    )
    assert personality.status_code == 200
    pid = personality.json()["id"]

    looks = await client.post(
        "/api/looks",
        json={
            "name": f"{name} look",
            "age": 24,
            "gender": "Female",
            "ethnicity": "Slavic",
            "nationality": "Russian",
            "hair_color": "Blonde",
            "body": {"height": "5'7\"", "breast_size": "Medium"},
        },
    )
    assert looks.status_code == 200
    lid = looks.json()["id"]

    inf = await client.post(
        "/api/influencers",
        json={"personality_id": pid, "looks_id": lid, "name": name},
    )
    assert inf.status_code == 200
    return int(inf.json()["id"])


@pytest.mark.asyncio
async def test_list_detail_and_archive(client: AsyncClient) -> None:
    iid = await _create_influencer(client, "Nova")

    listed = await client.get("/api/influencers")
    assert listed.status_code == 200
    rows = listed.json()
    assert any(r["id"] == iid for r in rows)
    match = next(r for r in rows if r["id"] == iid)
    assert match["generation_count"] == 0
    assert match["niche"] == "Lifestyle"
    assert match["age_rating"] == "Adult"

    detail = await client.get(f"/api/influencers/{iid}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["name"] == "Nova"
    assert body["personality"]["niche"] == "Lifestyle"
    assert body["looks"]["gender"] == "Female"
    assert body["looks"]["body"]["height"] == "5'7\""

    missing = await client.get("/api/influencers/99999")
    assert missing.status_code == 404

    archived = await client.post(f"/api/influencers/{iid}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    listed_after = await client.get("/api/influencers")
    assert all(r["id"] != iid for r in listed_after.json())

    detail_after = await client.get(f"/api/influencers/{iid}")
    assert detail_after.status_code == 404


@pytest.mark.asyncio
async def test_face_lock_from_generation(client: AsyncClient) -> None:
    from forge_python import config
    from forge_python.orchestrator import db

    iid = await _create_influencer(client, "LockMe")
    out = config.settings.generations_dir / "lock_test.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    cur = await db.execute(
        """
        INSERT INTO generations(
            influencer_id, user_prompt, expanded_prompt, workflow_type,
            model_used, llm_used, aspect_ratio, status, output_path, is_nsfw, is_vaulted
        ) VALUES (?, ?, ?, 'image', 'stub', 'template', '9:16', 'completed', ?, 0, 0)
        """,
        (iid, "full body studio portrait", "full body studio portrait", str(out)),
    )
    gid = int(cur.lastrowid)

    locked = await client.post(
        f"/api/influencers/{iid}/face-lock",
        json={"generation_id": gid},
    )
    assert locked.status_code == 200
    body = locked.json()
    assert body["face_lock"] == "base_portrait"
    assert body["looks"]["base_portrait_path"] == str(out)

    cleared = await client.post(
        f"/api/influencers/{iid}/face-lock",
        json={"clear": True},
    )
    assert cleared.status_code == 200
    assert cleared.json()["face_lock"] in ("none", None)
    assert not cleared.json()["looks"].get("base_portrait_path")


@pytest.mark.asyncio
async def test_patch_personality_and_looks_face_lock_stale(client: AsyncClient) -> None:
    from forge_python import config
    from forge_python.orchestrator import db

    iid = await _create_influencer(client, "Editable")
    detail = await client.get(f"/api/influencers/{iid}")
    assert detail.status_code == 200
    pid = detail.json()["personality_id"]
    lid = detail.json()["looks_id"]

    patched_p = await client.patch(
        f"/api/personalities/{pid}",
        json={"name": "Editable Two", "niche": "Fitness", "age_rating": "18+"},
    )
    assert patched_p.status_code == 200
    assert patched_p.json()["name"] == "Editable Two"
    assert patched_p.json()["niche"] == "Fitness"

    listed = await client.get("/api/influencers")
    assert any(r["id"] == iid and r["name"] == "Editable Two" for r in listed.json())

    # Lock face then change hair → stale warning
    out = config.settings.generations_dir / "edit_lock.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    cur = await db.execute(
        """
        INSERT INTO generations(
            influencer_id, user_prompt, expanded_prompt, workflow_type,
            model_used, llm_used, aspect_ratio, status, output_path, is_nsfw, is_vaulted
        ) VALUES (?, 'p', 'p', 'image', 'stub', 'template', '9:16', 'completed', ?, 0, 0)
        """,
        (iid, str(out)),
    )
    gid = int(cur.lastrowid)
    await client.post(f"/api/influencers/{iid}/face-lock", json={"generation_id": gid})

    patched_l = await client.patch(
        f"/api/looks/{lid}",
        json={"hair_style": "Curly long", "hair_color": "Red", "nationality": "Ukrainian"},
    )
    assert patched_l.status_code == 200
    body = patched_l.json()
    assert body["hair_style"] == "Curly long"
    assert body["nationality"] == "Ukrainian"
    assert body["face_lock_stale"] is True
    assert body.get("base_portrait_path")  # lock kept
    assert "Ukrainian" in (body.get("base_prompt") or "")


@pytest.mark.asyncio
async def test_delete_generation_removes_media(client: AsyncClient) -> None:
    from forge_python import config
    from forge_python.orchestrator import db

    iid = await _create_influencer(client, "Poster")
    out = config.settings.generations_dir / "99.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    await db.execute(
        """
        INSERT INTO generations(
            influencer_id, user_prompt, expanded_prompt, workflow_type,
            model_used, llm_used, aspect_ratio, status, output_path, is_nsfw, is_vaulted
        ) VALUES (?, 'p', 'p', 'image', 'stub', 'template', '9:16', 'completed', ?, 0, 0)
        """,
        (iid, str(out)),
    )
    row = await db.fetchone("SELECT id FROM generations WHERE influencer_id = ?", (iid,))
    assert row
    gid = int(row["id"])
    deleted = await client.delete(f"/api/generations/{gid}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert not out.exists()
    assert (await client.get(f"/api/generations/{gid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_influencer_removes_generations(client: AsyncClient) -> None:
    from forge_python import config
    from forge_python.orchestrator import db

    iid = await _create_influencer(client, "Doomed")
    out = config.settings.generations_dir / "doom.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    await db.execute(
        """
        INSERT INTO generations(
            influencer_id, user_prompt, expanded_prompt, workflow_type,
            model_used, llm_used, aspect_ratio, status, output_path, is_nsfw, is_vaulted
        ) VALUES (?, 'p', 'p', 'image', 'stub', 'template', '9:16', 'completed', ?, 0, 0)
        """,
        (iid, str(out)),
    )
    deleted = await client.delete(f"/api/influencers/{iid}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert deleted.json()["generations_removed"] >= 1
    assert not out.exists()
    assert (await client.get(f"/api/influencers/{iid}")).status_code == 404


@pytest.mark.asyncio
async def test_wardrobe_assign_and_list(client: AsyncClient) -> None:
    iid = await _create_influencer(client, "Dressed")
    created = await client.post(
        "/api/wardrobe",
        json={
            "name": "Cute red bikini",
            "category": "Swimwear",
            "prompt_keywords": "small cute red bikini, matching bottoms",
            "is_shared": False,
        },
    )
    assert created.status_code == 200
    wid = created.json()["id"]
    assigned = await client.post(f"/api/influencers/{iid}/wardrobe/{wid}")
    assert assigned.status_code == 200
    listed = await client.get(f"/api/influencers/{iid}/wardrobe")
    assert listed.status_code == 200
    assert any(w["id"] == wid for w in listed.json())


@pytest.mark.asyncio
async def test_regenerate_clears_seed(client: AsyncClient) -> None:
    """Regenerate must not reuse the parent seed (identical ComfyUI output)."""
    import forge_python.orchestrator as orch
    from forge_python.orchestrator import db

    iid = await _create_influencer(client, "Reroll")
    cur = await db.execute(
        """
        INSERT INTO generations(
            influencer_id, user_prompt, expanded_prompt, workflow_type,
            model_used, llm_used, aspect_ratio, seed, status, is_nsfw, is_vaulted
        ) VALUES (?, 'identity shot', 'identity shot', 'image',
                  'stub', 'template', '9:16', 123456789, 'completed', 0, 0)
        """,
        (iid,),
    )
    parent_id = int(cur.lastrowid)

    class _QuietQueue:
        async def enqueue(self, generation_id: int, *, require_real: bool = False) -> None:
            await db.execute(
                "UPDATE generations SET status = 'queued' WHERE id = ?",
                (generation_id,),
            )

    orch.queue = _QuietQueue()  # type: ignore[assignment]
    try:
        resp = await client.post(f"/api/generations/{parent_id}/regenerate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["parent_generation_id"] == parent_id
        assert body["seed"] is None
        assert body["user_prompt"] == "identity shot"
    finally:
        orch.queue = None


@pytest.mark.asyncio
async def test_generation_batch_queues_distinct_null_seeds(client: AsyncClient) -> None:
    """Batch identity shots: N queued rows, each with a fresh (null) seed."""
    import forge_python.orchestrator as orch
    from forge_python.orchestrator import db

    iid = await _create_influencer(client, "BatchFace")
    enqueued: list[int] = []

    class _QuietQueue:
        async def enqueue(self, generation_id: int, *, require_real: bool = False) -> None:
            enqueued.append(generation_id)
            await db.execute(
                "UPDATE generations SET status = 'queued' WHERE id = ?",
                (generation_id,),
            )

    orch.queue = _QuietQueue()  # type: ignore[assignment]
    try:
        resp = await client.post(
            "/api/generations/batch",
            json={
                "influencer_id": iid,
                "user_prompt": "full body identity shot, studio",
                "aspect_ratio": "9:16",
                "workflow_type": "image",
                "is_nsfw": False,
                "count": 3,
            },
        )
        assert resp.status_code == 200, resp.text
        gens = resp.json()["generations"]
        assert len(gens) == 3
        ids = [g["id"] for g in gens]
        assert len(set(ids)) == 3
        assert all(g["seed"] is None for g in gens)
        assert all(g["status"] == "queued" for g in gens)
        assert enqueued == ids
    finally:
        orch.queue = None


async def _create_influencer_rated(
    client: AsyncClient,
    *,
    name: str,
    age_rating: str,
    looks_age: int = 24,
) -> int:
    personality = await client.post(
        "/api/personalities",
        json={
            "name": name,
            "bio": "Test",
            "traits": {},
            "niche": "Lifestyle",
            "age_rating": age_rating,
        },
    )
    assert personality.status_code == 200
    looks = await client.post(
        "/api/looks",
        json={
            "name": f"{name} look",
            "age": looks_age,
            "gender": "Female",
            "body": {"height": 'Very short (under 4\'11" / 150cm)'},
        },
    )
    assert looks.status_code == 200
    inf = await client.post(
        "/api/influencers",
        json={
            "personality_id": personality.json()["id"],
            "looks_id": looks.json()["id"],
            "name": name,
        },
    )
    assert inf.status_code == 200
    return int(inf.json()["id"])


@pytest.mark.asyncio
async def test_nsfw_adult_allowed_teen_blocked(client: AsyncClient) -> None:
    import forge_python.orchestrator as orch
    from forge_python.orchestrator import db

    class _QuietQueue:
        async def enqueue(self, generation_id: int, *, require_real: bool = False) -> None:
            await db.execute(
                "UPDATE generations SET status = 'queued' WHERE id = ?",
                (generation_id,),
            )

    orch.queue = _QuietQueue()  # type: ignore[assignment]
    try:
        adult_id = await _create_influencer_rated(client, name="AdultNSFW", age_rating="Adult")
        ok = await client.post(
            "/api/generations",
            json={
                "influencer_id": adult_id,
                "user_prompt": "full body nude studio",
                "is_nsfw": True,
                "workflow_type": "image",
            },
        )
        assert ok.status_code == 200, ok.text
        assert ok.json()["is_nsfw"] is True

        teen_id = await _create_influencer_rated(client, name="TeenNSFW", age_rating="Teen")
        blocked = await client.post(
            "/api/generations",
            json={
                "influencer_id": teen_id,
                "user_prompt": "full body nude studio",
                "is_nsfw": True,
                "workflow_type": "image",
            },
        )
        assert blocked.status_code == 400
        assert "Adult" in blocked.text
    finally:
        orch.queue = None


@pytest.mark.asyncio
async def test_nsfw_blocked_when_looks_under_18(client: AsyncClient) -> None:
    import forge_python.orchestrator as orch

    class _QuietQueue:
        async def enqueue(self, generation_id: int, *, require_real: bool = False) -> None:
            return None

    orch.queue = _QuietQueue()  # type: ignore[assignment]
    try:
        iid = await _create_influencer_rated(
            client, name="YoungLooks", age_rating="Adult", looks_age=17
        )
        resp = await client.post(
            "/api/generations",
            json={
                "influencer_id": iid,
                "user_prompt": "full body nude studio",
                "is_nsfw": True,
                "workflow_type": "image",
            },
        )
        assert resp.status_code == 400
        assert "18" in resp.text
    finally:
        orch.queue = None
