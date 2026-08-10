"""FastAPI orchestrator entrypoint for InfluencerForge."""

from __future__ import annotations

import logging
import shutil
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from forge_python import __version__
from forge_python.config import settings
from forge_python.db import Database, body_from_json, body_to_json, traits_from_json, traits_to_json
from forge_python.face_seed import extract_face_embedding
from forge_python.llm_manager import (
    build_looks_prompt,
    build_system_prompt,
    expand_prompt,
    prompt_implies_nsfw,
    resolve_face_lock_path,
    resolve_negative_prompt,
    smart_daily_suggestions,
)
from forge_python.prompt_layers import ClothingConflictError, resolve_prompt_layers
from forge_python.model_downloader import ModelDownloader
from forge_python.models import (
    BootstrapStatus,
    FaceLockRequest,
    Generation,
    GenerationCreate,
    GenerationReplace,
    HealthResponse,
    Influencer,
    InfluencerCreate,
    GenerationBatchCreate,
    GenerationBatchResponse,
    GoogleCodeExchange,
    InfluencerDetail,
    Looks,
    LooksCreate,
    LooksUpdate,
    LooksUpdateResponse,
    Personality,
    PersonalityCreate,
    PersonalityUpdate,
    PostProcessRequest,
    QueueStatus,
    ResetRequest,
    Schedule,
    ScheduleCreate,
    SchedulePatch,
    SettingItem,
    SystemStats,
    VaultSetup,
    VaultUnlock,
    WardrobeCreate,
    WardrobeItem,
)
from forge_python import calendar_sync
from forge_python.ics_export import build_calendar
from forge_python.lip_sync import resolve_audio_path
from forge_python.post_processing import process_image
from forge_python.queue_worker import QueueWorker
from forge_python.readiness import (
    animatediff_custom_node_installed,
    collect_readiness,
    find_motion_module,
    workflow_ready,
)
from forge_python.reset import reset_app_data
from forge_python.scheduler import ScheduleService
from forge_python.system_monitor import collect_stats
from forge_python.vault import VaultService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forge.orchestrator")

db = Database()
downloader = ModelDownloader()
queue: QueueWorker | None = None
schedules: ScheduleService | None = None
vault: VaultService | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global queue, schedules, vault
    settings.ensure_directories()
    await db.connect()
    await downloader.run_bootstrap()
    vault = VaultService(db)
    queue = QueueWorker(db, vault=vault)
    schedules = ScheduleService(db)
    await queue.start()
    schedules.start()
    logger.info("Orchestrator ready on %s:%s", settings.host, settings.port)
    yield
    if queue is not None:
        queue.comfy.stop_process()
    if schedules:
        schedules.shutdown()
    await db.close()


app = FastAPI(title="InfluencerForge Orchestrator", version=__version__, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_queue() -> QueueWorker:
    if queue is None:
        raise HTTPException(503, "Queue not ready")
    return queue


def _require_vault() -> VaultService:
    if vault is None:
        raise HTTPException(503, "Vault not ready")
    return vault


def _require_schedules() -> ScheduleService:
    if schedules is None:
        raise HTTPException(503, "Scheduler not ready")
    return schedules


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    epoch = "0"
    try:
        epoch = (await db.get_setting("media_epoch")) or "0"
    except Exception:
        # DB may be mid-reset / not connected during early probes.
        epoch = "0"
    return HealthResponse(
        status="ok",
        version=__version__,
        data_dir=str(settings.data_dir),
        api="influencerforge",
        features=["readiness", "reset", "comfyui", "influencer_detail"],
        media_epoch=epoch,
    )


@app.get("/api/bootstrap/status", response_model=BootstrapStatus)
async def bootstrap_status() -> BootstrapStatus:
    st = downloader.state
    return BootstrapStatus(
        ready=st.ready,
        progress=st.progress,
        stage=st.stage,
        message=st.message,
        steps=st.steps,
    )


@app.get("/api/comfyui/status")
async def comfyui_status() -> dict[str, Any]:
    if queue is None:
        from forge_python.comfyui_client import ComfyUIClient

        return await ComfyUIClient().status()
    return await queue.comfy.status()


@app.get("/api/readiness")
async def readiness() -> dict[str, Any]:
    comfy = queue.comfy if queue is not None else None
    return await collect_readiness(comfy)


@app.get("/api/queue", response_model=QueueStatus)
async def queue_status() -> QueueStatus:
    q = _require_queue()
    data = q.status()
    return QueueStatus(
        pending=int(data["pending"]),
        processing=int(data["processing"]),
        paused=bool(data["paused"]),
    )


@app.post("/api/queue/pause")
async def queue_pause() -> dict[str, str]:
    _require_queue().pause()
    return {"status": "paused"}


@app.post("/api/queue/resume")
async def queue_resume() -> dict[str, str]:
    _require_queue().resume()
    return {"status": "resumed"}


@app.get("/api/system/stats", response_model=SystemStats)
async def system_stats() -> SystemStats:
    q = _require_queue().status()
    return collect_stats(int(q["pending"]), int(q["processing"]))


@app.get("/api/suggestions")
async def suggestions(niche: str = "Lifestyle") -> dict[str, list[str]]:
    return {"suggestions": smart_daily_suggestions(niche)}


# --- Personalities ---
@app.get("/api/personalities", response_model=list[Personality])
async def list_personalities() -> list[Personality]:
    rows = await db.fetchall("SELECT * FROM personalities ORDER BY id DESC")
    return [
        Personality(
            id=r["id"],
            name=r["name"],
            bio=r["bio"],
            traits=traits_from_json(r["traits"]),
            niche=r["niche"],
            age_rating=r["age_rating"],
            system_prompt=r["system_prompt"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@app.post("/api/personalities", response_model=Personality)
async def create_personality(body: PersonalityCreate) -> Personality:
    system_prompt = build_system_prompt(body.name, body.bio, body.traits, body.niche)
    cur = await db.execute(
        """
        INSERT INTO personalities(name, bio, traits, niche, age_rating, system_prompt)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        (
            body.name,
            body.bio,
            traits_to_json(body.traits),
            body.niche,
            body.age_rating,
            system_prompt,
        ),
    )
    pid = cur.lastrowid
    assert pid is not None
    return Personality(id=int(pid), system_prompt=system_prompt, **body.model_dump())


@app.patch("/api/personalities/{personality_id}", response_model=Personality)
async def update_personality(personality_id: int, body: PersonalityUpdate) -> Personality:
    row = await db.fetchone("SELECT * FROM personalities WHERE id = ?", (personality_id,))
    if not row:
        raise HTTPException(404, "Personality not found")
    patch = body.model_dump(exclude_unset=True)
    name = patch.get("name", row["name"])
    bio = patch.get("bio", row["bio"])
    traits = patch.get("traits", traits_from_json(row["traits"]))
    niche = patch.get("niche", row["niche"])
    age_rating = patch.get("age_rating", row["age_rating"])
    system_prompt = build_system_prompt(name, bio, traits, niche)
    await db.execute(
        """
        UPDATE personalities
        SET name = ?, bio = ?, traits = ?, niche = ?, age_rating = ?, system_prompt = ?
        WHERE id = ?
        """,
        (name, bio, traits_to_json(traits), niche, age_rating, system_prompt, personality_id),
    )
    # Keep influencer display name in sync when personality name changes.
    if "name" in patch:
        await db.execute(
            "UPDATE influencers SET name = ? WHERE personality_id = ? AND is_active = 1",
            (name, personality_id),
        )
    return Personality(
        id=personality_id,
        name=name,
        bio=bio,
        traits=traits,
        niche=niche,
        age_rating=age_rating,
        system_prompt=system_prompt,
        created_at=row.get("created_at"),
    )


# --- Looks ---
@app.get("/api/looks", response_model=list[Looks])
async def list_looks() -> list[Looks]:
    rows = await db.fetchall("SELECT * FROM looks ORDER BY id DESC")
    return [_looks_from_row(r) for r in rows]


@app.post("/api/looks", response_model=Looks)
async def create_looks(body: LooksCreate) -> Looks:
    base_prompt = body.base_prompt or build_looks_prompt(
        age=body.age,
        ethnicity=body.ethnicity,
        nationality=body.nationality,
        hair_color=body.hair_color,
        hair_style=body.hair_style,
        eye_color=body.eye_color,
        style=body.style,
        gender=body.gender,
        body=body.body,
    )
    cur = await db.execute(
        """
        INSERT INTO looks(name, age, gender, ethnicity, nationality, hair_color, hair_style,
                          eye_color, style, body_json, base_prompt, reference_image_path)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.name,
            body.age,
            body.gender,
            body.ethnicity,
            body.nationality,
            body.hair_color,
            body.hair_style,
            body.eye_color,
            body.style,
            body_to_json(body.body),
            base_prompt,
            body.reference_image_path,
        ),
    )
    lid = cur.lastrowid
    assert lid is not None
    data = body.model_dump()
    data["base_prompt"] = base_prompt
    return Looks(id=int(lid), **data)


@app.patch("/api/looks/{looks_id}", response_model=LooksUpdateResponse)
async def update_looks(looks_id: int, body: LooksUpdate) -> LooksUpdateResponse:
    row = await db.fetchone("SELECT * FROM looks WHERE id = ?", (looks_id,))
    if not row:
        raise HTTPException(404, "Looks not found")
    patch = body.model_dump(exclude_unset=True)
    identity_keys = {"ethnicity", "nationality", "hair_color", "hair_style", "eye_color"}
    had_face_lock = bool(row.get("base_portrait_path") or row.get("reference_image_path"))
    face_lock_stale = had_face_lock and bool(identity_keys & set(patch.keys()))

    name = patch.get("name", row["name"])
    age = patch.get("age", row["age"])
    gender = patch.get("gender", row.get("gender") or "Female")
    ethnicity = patch.get("ethnicity", row["ethnicity"])
    nationality = patch.get("nationality", row.get("nationality"))
    hair_color = patch.get("hair_color", row["hair_color"])
    hair_style = patch.get("hair_style", row["hair_style"])
    eye_color = patch.get("eye_color", row["eye_color"])
    style = patch.get("style", row["style"])
    body_map = patch.get("body", body_from_json(row.get("body_json")))
    base_prompt = build_looks_prompt(
        age=age,
        ethnicity=ethnicity,
        nationality=nationality,
        hair_color=hair_color,
        hair_style=hair_style,
        eye_color=eye_color,
        style=style,
        gender=gender,
        body=body_map,
    )
    await db.execute(
        """
        UPDATE looks
        SET name = ?, age = ?, gender = ?, ethnicity = ?, nationality = ?, hair_color = ?,
            hair_style = ?, eye_color = ?, style = ?, body_json = ?, base_prompt = ?
        WHERE id = ?
        """,
        (
            name,
            age,
            gender,
            ethnicity,
            nationality,
            hair_color,
            hair_style,
            eye_color,
            style,
            body_to_json(body_map),
            base_prompt,
            looks_id,
        ),
    )
    updated = await db.fetchone("SELECT * FROM looks WHERE id = ?", (looks_id,))
    assert updated
    looks = _looks_from_row(updated)
    return LooksUpdateResponse(**looks.model_dump(), face_lock_stale=face_lock_stale)


@app.post("/api/looks/{looks_id}/face-seed", response_model=Looks)
async def upload_face_seed(looks_id: int, file: UploadFile) -> Looks:
    row = await db.fetchone("SELECT * FROM looks WHERE id = ?", (looks_id,))
    if not row:
        raise HTTPException(404, "Looks not found")
    settings.ensure_directories()
    dest = settings.uploads_dir / f"face_{looks_id}_{file.filename or 'seed.png'}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    embedding = extract_face_embedding(dest)
    await db.execute(
        "UPDATE looks SET reference_image_path = ?, face_embedding = ? WHERE id = ?",
        (str(dest), embedding, looks_id),
    )
    updated = await db.fetchone("SELECT * FROM looks WHERE id = ?", (looks_id,))
    assert updated
    return _looks_from_row(updated)


@app.post("/api/uploads/audio")
async def upload_audio(file: UploadFile) -> dict[str, str]:
    """Store audio for talking-head / lip-sync jobs. Returns a path for GenerationCreate.audio_path."""
    name = (file.filename or "audio.wav").replace("/", "_").replace("\\", "_")
    suffix = Path(name).suffix.lower()
    if suffix not in {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}:
        raise HTTPException(400, "Audio must be wav, mp3, m4a, aac, ogg, or flac")
    settings.ensure_directories()
    dest = settings.uploads_dir / f"audio_{int(time.time() * 1000)}_{name}"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    if dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "Empty audio upload")
    return {"path": str(dest), "filename": dest.name}


def _looks_from_row(r: dict[str, Any]) -> Looks:
    return Looks(
        id=r["id"],
        name=r["name"],
        age=r["age"],
        gender=r.get("gender") or "Female",
        ethnicity=r["ethnicity"],
        nationality=r.get("nationality"),
        hair_color=r["hair_color"],
        hair_style=r["hair_style"],
        eye_color=r["eye_color"],
        style=r["style"],
        body=body_from_json(r.get("body_json")),
        base_prompt=r["base_prompt"],
        reference_image_path=r["reference_image_path"],
        face_embedding="present" if r.get("face_embedding") else None,
        lora_path=r["lora_path"],
        base_portrait_path=r["base_portrait_path"],
        created_at=r["created_at"],
    )


async def _resolve_avatar_path(influencer_id: int, looks_id: int) -> str | None:
    """Best available preview: base portrait → face seed → latest completed generation."""
    looks = await db.fetchone("SELECT * FROM looks WHERE id = ?", (looks_id,))
    if looks:
        for key in ("base_portrait_path", "reference_image_path"):
            val = looks.get(key)
            if val:
                return str(val)
    latest = await db.fetchone(
        """
        SELECT output_thumbnail_path, output_path, teaser_path FROM generations
        WHERE influencer_id = ? AND status = 'completed'
        ORDER BY id DESC LIMIT 1
        """,
        (influencer_id,),
    )
    if latest:
        return (
            str(
                latest.get("output_thumbnail_path")
                or latest.get("output_path")
                or latest.get("teaser_path")
                or ""
            )
            or None
        )
    return None


def _face_lock_from_looks(looks: dict[str, Any] | None) -> str:
    if not looks:
        return "none"
    ref = looks.get("reference_image_path")
    if ref and Path(str(ref)).is_file():
        return "face_seed"
    portrait = looks.get("base_portrait_path")
    if portrait and Path(str(portrait)).is_file():
        return "base_portrait"
    return "none"


async def _generation_count(influencer_id: int) -> int:
    row = await db.fetchone(
        "SELECT COUNT(*) AS c FROM generations WHERE influencer_id = ?",
        (influencer_id,),
    )
    return int((row or {}).get("c") or 0)


def _influencer_from_row(
    r: dict[str, Any],
    *,
    avatar_path: str | None = None,
    age_rating: str | None = None,
    niche: str | None = None,
    face_lock: str | None = None,
    generation_count: int = 0,
) -> Influencer:
    return Influencer(
        id=r["id"],
        personality_id=r["personality_id"],
        looks_id=r["looks_id"],
        name=r["name"],
        is_active=bool(r["is_active"]),
        created_at=r.get("created_at"),
        avatar_path=avatar_path,
        age_rating=age_rating,
        niche=niche,
        face_lock=face_lock or "none",
        generation_count=generation_count,
    )


async def _build_influencer(r: dict[str, Any]) -> Influencer:
    avatar = await _resolve_avatar_path(int(r["id"]), int(r["looks_id"]))
    personality = await db.fetchone(
        "SELECT age_rating, niche FROM personalities WHERE id = ?",
        (r["personality_id"],),
    )
    looks = await db.fetchone("SELECT * FROM looks WHERE id = ?", (r["looks_id"],))
    return _influencer_from_row(
        r,
        avatar_path=avatar,
        age_rating=(personality or {}).get("age_rating"),
        niche=(personality or {}).get("niche"),
        face_lock=_face_lock_from_looks(looks),
        generation_count=await _generation_count(int(r["id"])),
    )


# --- Influencers ---
@app.get("/api/influencers", response_model=list[Influencer])
async def list_influencers() -> list[Influencer]:
    rows = await db.fetchall("SELECT * FROM influencers WHERE is_active = 1 ORDER BY id DESC")
    return [await _build_influencer(r) for r in rows]


@app.get("/api/influencers/{influencer_id}", response_model=InfluencerDetail)
async def get_influencer(influencer_id: int) -> InfluencerDetail:
    row = await db.fetchone("SELECT * FROM influencers WHERE id = ?", (influencer_id,))
    if not row or not row["is_active"]:
        raise HTTPException(404, "Influencer not found")
    base = await _build_influencer(row)
    personality_row = await db.fetchone(
        "SELECT * FROM personalities WHERE id = ?",
        (row["personality_id"],),
    )
    looks_row = await db.fetchone("SELECT * FROM looks WHERE id = ?", (row["looks_id"],))
    personality = None
    if personality_row:
        personality = Personality(
            id=personality_row["id"],
            name=personality_row["name"],
            bio=personality_row["bio"],
            traits=traits_from_json(personality_row["traits"]),
            niche=personality_row["niche"],
            age_rating=personality_row["age_rating"],
            system_prompt=personality_row["system_prompt"],
            created_at=personality_row["created_at"],
        )
    looks = _looks_from_row(looks_row) if looks_row else None
    return InfluencerDetail(**base.model_dump(), personality=personality, looks=looks)


@app.post("/api/influencers", response_model=Influencer)
async def create_influencer(body: InfluencerCreate) -> Influencer:
    personality = await db.fetchone("SELECT * FROM personalities WHERE id = ?", (body.personality_id,))
    looks = await db.fetchone("SELECT * FROM looks WHERE id = ?", (body.looks_id,))
    if not personality or not looks:
        raise HTTPException(400, "Invalid personality_id or looks_id")
    name = body.name or personality["name"]
    cur = await db.execute(
        "INSERT INTO influencers(personality_id, looks_id, name) VALUES(?, ?, ?)",
        (body.personality_id, body.looks_id, name),
    )
    iid = cur.lastrowid
    assert iid is not None
    row = await db.fetchone("SELECT * FROM influencers WHERE id = ?", (int(iid),))
    assert row
    return await _build_influencer(row)


@app.post("/api/influencers/{influencer_id}/archive")
async def archive_influencer(influencer_id: int) -> dict[str, str]:
    row = await db.fetchone("SELECT id FROM influencers WHERE id = ?", (influencer_id,))
    if not row:
        raise HTTPException(404, "Influencer not found")
    await db.execute("UPDATE influencers SET is_active = 0 WHERE id = ?", (influencer_id,))
    return {"status": "archived"}


@app.delete("/api/influencers/{influencer_id}")
async def delete_influencer(influencer_id: int) -> dict[str, Any]:
    """Hard-delete influencer and all their generations + media files."""
    row = await db.fetchone("SELECT * FROM influencers WHERE id = ?", (influencer_id,))
    if not row:
        raise HTTPException(404, "Influencer not found")
    gens = await db.fetchall(
        "SELECT * FROM generations WHERE influencer_id = ?",
        (influencer_id,),
    )
    removed_files = sum(_unlink_generation_media(gen) for gen in gens)
    await db.execute("DELETE FROM influencer_wardrobe WHERE influencer_id = ?", (influencer_id,))
    await db.execute("DELETE FROM schedules WHERE influencer_id = ?", (influencer_id,))
    await db.execute("DELETE FROM generations WHERE influencer_id = ?", (influencer_id,))
    await db.execute("DELETE FROM influencers WHERE id = ?", (influencer_id,))
    return {"status": "deleted", "generations_removed": len(gens), "files_removed": removed_files}


@app.post("/api/influencers/{influencer_id}/face-lock", response_model=InfluencerDetail)
async def lock_influencer_face(influencer_id: int, body: FaceLockRequest) -> InfluencerDetail:
    """Set or clear the look's base portrait used for face-consistent img2img."""
    row = await db.fetchone("SELECT * FROM influencers WHERE id = ? AND is_active = 1", (influencer_id,))
    if not row:
        raise HTTPException(404, "Influencer not found")
    looks_id = int(row["looks_id"])

    if body.clear:
        await db.execute(
            "UPDATE looks SET base_portrait_path = NULL WHERE id = ?",
            (looks_id,),
        )
        return await get_influencer(influencer_id)

    if body.generation_id is None:
        raise HTTPException(400, "generation_id required unless clear=true")

    gen = await db.fetchone("SELECT * FROM generations WHERE id = ?", (body.generation_id,))
    if not gen or int(gen["influencer_id"]) != influencer_id:
        raise HTTPException(404, "Generation not found for this influencer")
    if gen["status"] != "completed":
        raise HTTPException(400, "Generation is not completed yet")
    if gen["is_nsfw"] or gen["is_vaulted"]:
        raise HTTPException(400, "Use an SFW (non-vaulted) shot for face lock")

    path = gen.get("output_path") or gen.get("output_thumbnail_path")
    if not path or not Path(str(path)).is_file():
        raise HTTPException(400, "Generation has no usable image file")

    await db.execute(
        "UPDATE looks SET base_portrait_path = ? WHERE id = ?",
        (str(path), looks_id),
    )
    return await get_influencer(influencer_id)


# --- Wardrobe ---
@app.get("/api/wardrobe", response_model=list[WardrobeItem])
async def list_wardrobe() -> list[WardrobeItem]:
    rows = await db.fetchall("SELECT * FROM wardrobe_items ORDER BY id DESC")
    return [WardrobeItem(**r) for r in rows]


@app.post("/api/wardrobe", response_model=WardrobeItem)
async def create_wardrobe(body: WardrobeCreate) -> WardrobeItem:
    cur = await db.execute(
        """
        INSERT INTO wardrobe_items(name, description, category, prompt_keywords, preview_image, is_shared)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        (
            body.name,
            body.description,
            body.category,
            body.prompt_keywords,
            body.preview_image,
            int(body.is_shared),
        ),
    )
    wid = cur.lastrowid
    assert wid is not None
    return WardrobeItem(id=int(wid), **body.model_dump())


@app.get("/api/influencers/{influencer_id}/wardrobe", response_model=list[WardrobeItem])
async def list_influencer_wardrobe(influencer_id: int) -> list[WardrobeItem]:
    """Outfits assigned to this influencer, plus shared wardrobe items."""
    rows = await db.fetchall(
        """
        SELECT w.* FROM wardrobe_items w
        WHERE w.is_shared = 1
           OR w.id IN (
                SELECT wardrobe_item_id FROM influencer_wardrobe WHERE influencer_id = ?
           )
        ORDER BY w.id DESC
        """,
        (influencer_id,),
    )
    return [WardrobeItem(**r) for r in rows]


@app.post("/api/influencers/{influencer_id}/wardrobe/{item_id}")
async def assign_wardrobe(influencer_id: int, item_id: int) -> dict[str, str]:
    inf = await db.fetchone("SELECT id FROM influencers WHERE id = ?", (influencer_id,))
    item = await db.fetchone("SELECT id FROM wardrobe_items WHERE id = ?", (item_id,))
    if not inf or not item:
        raise HTTPException(404, "Influencer or wardrobe item not found")
    await db.execute(
        """
        INSERT OR IGNORE INTO influencer_wardrobe(influencer_id, wardrobe_item_id)
        VALUES(?, ?)
        """,
        (influencer_id, item_id),
    )
    return {"status": "assigned"}


@app.delete("/api/influencers/{influencer_id}/wardrobe/{item_id}")
async def unassign_wardrobe(influencer_id: int, item_id: int) -> dict[str, str]:
    await db.execute(
        "DELETE FROM influencer_wardrobe WHERE influencer_id = ? AND wardrobe_item_id = ?",
        (influencer_id, item_id),
    )
    return {"status": "unassigned"}


# --- Generations ---
@app.get("/api/generations", response_model=list[Generation])
async def list_generations(
    influencer_id: int | None = None,
    is_nsfw: bool | None = None,
) -> list[Generation]:
    sql = "SELECT * FROM generations WHERE 1=1"
    params: list[Any] = []
    if influencer_id is not None:
        sql += " AND influencer_id = ?"
        params.append(influencer_id)
    if is_nsfw is not None:
        sql += " AND is_nsfw = ?"
        params.append(int(is_nsfw))
    sql += " ORDER BY id DESC"
    rows = await db.fetchall(sql, tuple(params))
    return [Generation(**r) for r in rows]


@app.get("/api/generations/{generation_id}", response_model=Generation)
async def get_generation(generation_id: int) -> Generation:
    row = await db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
    if not row:
        raise HTTPException(404, "Not found")
    return Generation(**row)


def _unlink_generation_media(gen: dict[str, Any]) -> int:
    removed = 0
    for key in (
        "output_path",
        "output_thumbnail_path",
        "teaser_path",
        "vault_file_path",
    ):
        path = gen.get(key)
        if not path:
            continue
        p = Path(str(path))
        if p.is_file():
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
    return removed


@app.delete("/api/generations/{generation_id}")
async def delete_generation(generation_id: int) -> dict[str, Any]:
    """Hard-delete one post and its media (including vault ciphertext / teaser)."""
    row = await db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
    if not row:
        raise HTTPException(404, "Not found")
    if row["status"] in ("queued", "running"):
        raise HTTPException(400, "Wait for the job to finish (or fail) before deleting")

    removed_files = _unlink_generation_media(row)
    out = row.get("output_path")
    if out:
        await db.execute(
            "UPDATE looks SET base_portrait_path = NULL WHERE base_portrait_path = ?",
            (str(out),),
        )
    await db.execute(
        "UPDATE generations SET parent_generation_id = NULL WHERE parent_generation_id = ?",
        (generation_id,),
    )
    await db.execute("DELETE FROM generations WHERE id = ?", (generation_id,))
    return {"status": "deleted", "id": generation_id, "files_removed": removed_files}


_SEED_FROM_BODY = object()


def _assert_nsfw_allowed(*, is_nsfw: bool, looks: Any) -> None:
    """Looks under 18 cannot enqueue explicit jobs. Personality age_rating is not gated."""
    if not is_nsfw:
        return
    looks_age = None if looks is None else looks.get("age")
    if looks_age is not None:
        try:
            age_int = int(looks_age)
        except (TypeError, ValueError):
            age_int = None
        if age_int is not None and age_int < 18:
            raise HTTPException(
                400,
                "Explicit / NSFW requires the influencer looks age to be 18 or older.",
            )


async def _enqueue_generation(
    body: GenerationCreate,
    *,
    seed: Any = _SEED_FROM_BODY,
) -> Generation:
    """Validate, insert, and enqueue one generation.

    Pass ``seed=None`` to force a null seed (ComfyUI draws a new one). Omit to use ``body.seed``.
    """
    wardrobe_keywords = None
    wardrobe_id = body.wardrobe_item_id
    if wardrobe_id:
        item = await db.fetchone(
            "SELECT prompt_keywords FROM wardrobe_items WHERE id = ?",
            (wardrobe_id,),
        )
        if item:
            wardrobe_keywords = item["prompt_keywords"]
        else:
            wardrobe_id = None
            wardrobe_keywords = None
    influencer = await db.fetchone("SELECT * FROM influencers WHERE id = ?", (body.influencer_id,))
    if not influencer:
        raise HTTPException(400, "Invalid influencer_id")
    personality = await db.fetchone(
        "SELECT * FROM personalities WHERE id = ?",
        (influencer["personality_id"],),
    )
    looks = await db.fetchone("SELECT * FROM looks WHERE id = ?", (influencer["looks_id"],))
    age_rating = (personality or {}).get("age_rating") or "Family"
    try:
        layers = resolve_prompt_layers(
            body.user_prompt,
            wardrobe_keywords=wardrobe_keywords,
            is_nsfw_flag=body.is_nsfw,
        )
    except ClothingConflictError as exc:
        raise HTTPException(400, str(exc)) from exc
    is_nsfw = layers.is_nsfw
    _assert_nsfw_allowed(is_nsfw=is_nsfw, looks=looks)
    # Identity explore: selected traits only, no face-reference lock in the text stack.
    # Create-post with a lock: hybrid looks (body kept; hair/eyes from reference).
    has_face_ref = resolve_face_lock_path(looks) is not None
    if body.workflow_type == "lip_sync":
        if body.identity_explore:
            raise HTTPException(400, "Talking-head cannot use identity explore — needs a locked face")
        if not has_face_ref:
            raise HTTPException(
                400,
                "Talking-head needs a Face Seed or base portrait on the influencer look",
            )
        audio = resolve_audio_path(body.audio_path)
        if audio is None:
            raise HTTPException(400, "Talking-head needs audio — upload via /api/uploads/audio first")
    if body.workflow_type == "video":
        ad_ok = (
            workflow_ready("video_animate.json")
            and animatediff_custom_node_installed()
            and find_motion_module() is not None
        )
        if not ad_ok:
            raise HTTPException(
                400,
                "AnimateDiff video is not ready — install ComfyUI-AnimateDiff-Evolved, "
                "Video Helper Suite, an SDXL motion module, and ffmpeg "
                "(see readiness checklist / comfyui README).",
            )
    face_locked = has_face_ref and not body.identity_explore
    looks_prompt = build_looks_prompt(
        age=(looks or {}).get("age"),
        ethnicity=(looks or {}).get("ethnicity"),
        nationality=(looks or {}).get("nationality"),
        hair_color=(looks or {}).get("hair_color"),
        hair_style=(looks or {}).get("hair_style"),
        eye_color=(looks or {}).get("eye_color"),
        style=(looks or {}).get("style"),
        gender=(looks or {}).get("gender"),
        body=body_from_json((looks or {}).get("body_json")),
        for_nsfw=is_nsfw,
        face_locked=face_locked,
    )
    expanded = expand_prompt(
        layers.scene,
        influencer_name=influencer["name"],
        looks_prompt=looks_prompt or (looks or {}).get("base_prompt") or "",
        wardrobe_keywords=layers.wardrobe_keywords,
        system_prompt=(personality or {}).get("system_prompt"),
        is_nsfw=is_nsfw,
        face_locked=face_locked,
        clothing_from_wardrobe=layers.clothing_from_wardrobe,
    )
    negative = resolve_negative_prompt(
        is_nsfw=is_nsfw,
        user_prompt=layers.scene,
        wardrobe_keywords=layers.wardrobe_keywords,
        clothing_from_wardrobe=layers.clothing_from_wardrobe,
        age=(looks or {}).get("age"),
    )
    use_seed: int | None = body.seed if seed is _SEED_FROM_BODY else seed  # type: ignore[assignment]
    audio_store = None
    if body.workflow_type == "lip_sync" and body.audio_path:
        resolved = resolve_audio_path(body.audio_path)
        audio_store = str(resolved) if resolved else body.audio_path
    cur = await db.execute(
        """
        INSERT INTO generations(
            influencer_id, user_prompt, expanded_prompt, negative_prompt,
            workflow_type, model_used, llm_used,
            aspect_ratio, seed, steps, cfg_scale, is_nsfw, wardrobe_item_id,
            identity_explore, audio_path, status
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (
            body.influencer_id,
            body.user_prompt,
            expanded,
            negative,
            body.workflow_type,
            body.model_used,
            body.llm_used,
            body.aspect_ratio,
            use_seed,
            body.steps,
            body.cfg_scale,
            int(is_nsfw),
            wardrobe_id if layers.clothing_from_wardrobe else None,
            int(body.identity_explore),
            audio_store,
        ),
    )
    gid = cur.lastrowid
    assert gid is not None
    await _require_queue().enqueue(int(gid), require_real=body.require_real)
    row = await db.fetchone("SELECT * FROM generations WHERE id = ?", (gid,))
    assert row
    return Generation(**row)


@app.post("/api/generations", response_model=Generation)
async def create_generation(body: GenerationCreate) -> Generation:
    return await _enqueue_generation(body)


@app.post("/api/generations/batch", response_model=GenerationBatchResponse)
async def create_generation_batch(body: GenerationBatchCreate) -> GenerationBatchResponse:
    """Queue several copies of the same prompt with independent (null) seeds."""
    single = GenerationCreate(
        influencer_id=body.influencer_id,
        user_prompt=body.user_prompt,
        workflow_type=body.workflow_type,
        aspect_ratio=body.aspect_ratio,
        seed=None,
        steps=body.steps,
        cfg_scale=body.cfg_scale,
        wardrobe_item_id=body.wardrobe_item_id,
        is_nsfw=body.is_nsfw,
        model_used=body.model_used,
        llm_used=body.llm_used,
        require_real=body.require_real,
        identity_explore=body.identity_explore,
    )
    gens = [await _enqueue_generation(single, seed=None) for _ in range(body.count)]
    return GenerationBatchResponse(generations=gens)


@app.post("/api/generations/{generation_id}/regenerate", response_model=Generation)
async def regenerate(
    generation_id: int,
    require_real: bool = False,
    identity_explore: bool | None = None,
) -> Generation:
    parent = await db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
    if not parent:
        raise HTTPException(404, "Not found")
    influencer = await db.fetchone(
        "SELECT * FROM influencers WHERE id = ?",
        (parent["influencer_id"],),
    )
    looks = None
    if influencer:
        looks = await db.fetchone("SELECT * FROM looks WHERE id = ?", (influencer["looks_id"],))
    has_face = resolve_face_lock_path(looks) is not None
    # With a Face Seed, regenerate locks identity unless caller explicitly asks to explore.
    if identity_explore is not None:
        explore = bool(identity_explore)
    elif has_face:
        explore = False
    else:
        explore = bool(parent.get("identity_explore"))
    # Re-resolve via create path so wardrobe / explore rules stay consistent.
    child = await _enqueue_generation(
        GenerationCreate(
            influencer_id=int(parent["influencer_id"]),
            user_prompt=str(parent["user_prompt"]),
            workflow_type=parent["workflow_type"],
            aspect_ratio=parent["aspect_ratio"],
            seed=None,
            steps=int(parent["steps"] or 20),
            cfg_scale=float(parent["cfg_scale"] or 7.0),
            wardrobe_item_id=parent.get("wardrobe_item_id"),
            is_nsfw=bool(parent["is_nsfw"]),
            model_used=str(parent["model_used"] or "stub"),
            llm_used=str(parent["llm_used"] or "template"),
            require_real=require_real,
            identity_explore=explore,
            audio_path=parent.get("audio_path"),
        ),
        seed=None,
    )
    await db.execute(
        "UPDATE generations SET parent_generation_id = ? WHERE id = ?",
        (parent["id"], child.id),
    )
    row = await db.fetchone("SELECT * FROM generations WHERE id = ?", (child.id,))
    assert row
    return Generation(**row)


@app.post("/api/generations/{generation_id}/replace", response_model=Generation)
async def replace_generation(generation_id: int, body: GenerationReplace) -> Generation:
    """Overwrite an existing post with a new prompt/outfit (same id, new seed)."""
    row = await db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
    if not row:
        raise HTTPException(404, "Not found")
    if row.get("is_vaulted"):
        raise HTTPException(400, "Unvault or edit a non-vaulted post")

    influencer = await db.fetchone("SELECT * FROM influencers WHERE id = ?", (row["influencer_id"],))
    if not influencer:
        raise HTTPException(400, "Influencer missing")
    personality = await db.fetchone(
        "SELECT * FROM personalities WHERE id = ?",
        (influencer["personality_id"],),
    )
    looks = await db.fetchone("SELECT * FROM looks WHERE id = ?", (influencer["looks_id"],))
    age_rating = (personality or {}).get("age_rating") or "Family"
    wardrobe_id = body.wardrobe_item_id if body.wardrobe_item_id is not None else row.get("wardrobe_item_id")
    wardrobe_keywords = None
    if wardrobe_id:
        item = await db.fetchone(
            "SELECT prompt_keywords FROM wardrobe_items WHERE id = ?",
            (wardrobe_id,),
        )
        if item:
            wardrobe_keywords = item["prompt_keywords"]
        else:
            wardrobe_id = None
    nsfw_flag = bool(body.is_nsfw) if body.is_nsfw is not None else bool(row["is_nsfw"])
    try:
        layers = resolve_prompt_layers(
            body.user_prompt,
            wardrobe_keywords=wardrobe_keywords,
            is_nsfw_flag=nsfw_flag,
        )
    except ClothingConflictError as exc:
        raise HTTPException(400, str(exc)) from exc
    is_nsfw = layers.is_nsfw
    _assert_nsfw_allowed(is_nsfw=is_nsfw, looks=looks)

    face_locked = resolve_face_lock_path(looks) is not None
    looks_prompt = build_looks_prompt(
        age=(looks or {}).get("age"),
        ethnicity=(looks or {}).get("ethnicity"),
        nationality=(looks or {}).get("nationality"),
        hair_color=(looks or {}).get("hair_color"),
        hair_style=(looks or {}).get("hair_style"),
        eye_color=(looks or {}).get("eye_color"),
        style=(looks or {}).get("style"),
        gender=(looks or {}).get("gender"),
        body=body_from_json((looks or {}).get("body_json")),
        for_nsfw=is_nsfw,
        face_locked=face_locked,
    )
    expanded = expand_prompt(
        layers.scene,
        influencer_name=influencer["name"],
        looks_prompt=looks_prompt or (looks or {}).get("base_prompt") or "",
        wardrobe_keywords=layers.wardrobe_keywords,
        system_prompt=(personality or {}).get("system_prompt"),
        is_nsfw=is_nsfw,
        face_locked=face_locked,
        clothing_from_wardrobe=layers.clothing_from_wardrobe,
    )
    negative = resolve_negative_prompt(
        is_nsfw=is_nsfw,
        user_prompt=layers.scene,
        wardrobe_keywords=layers.wardrobe_keywords,
        clothing_from_wardrobe=layers.clothing_from_wardrobe,
        age=(looks or {}).get("age"),
    )
    wardrobe_id = wardrobe_id if layers.clothing_from_wardrobe else None
    workflow_type = body.workflow_type or row["workflow_type"]
    aspect_ratio = body.aspect_ratio or row["aspect_ratio"]

    # Drop old cleartext so a new file can take its place.
    for key in ("output_path", "output_thumbnail_path", "teaser_path"):
        path = row.get(key)
        if path and Path(str(path)).is_file():
            try:
                Path(str(path)).unlink()
            except OSError:
                pass

    await db.execute(
        """
        UPDATE generations
        SET user_prompt = ?,
            expanded_prompt = ?,
            negative_prompt = ?,
            workflow_type = ?,
            aspect_ratio = ?,
            seed = NULL,
            is_nsfw = ?,
            wardrobe_item_id = ?,
            output_path = NULL,
            output_thumbnail_path = NULL,
            teaser_path = NULL,
            error_message = NULL,
            status = 'pending',
            completed_at = NULL,
            model_used = 'stub'
        WHERE id = ?
        """,
        (
            body.user_prompt,
            expanded,
            negative,
            workflow_type,
            aspect_ratio,
            int(is_nsfw),
            None if is_nsfw else wardrobe_id,
            generation_id,
        ),
    )
    await _require_queue().enqueue(int(generation_id), require_real=body.require_real)
    updated = await db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
    assert updated
    return Generation(**updated)


@app.post("/api/post-process")
async def post_process(body: PostProcessRequest) -> dict[str, str]:
    row = await db.fetchone("SELECT * FROM generations WHERE id = ?", (body.generation_id,))
    if not row or not row["output_path"]:
        raise HTTPException(404, "Generation output missing")
    out = process_image(
        Path(row["output_path"]),
        rotate_degrees=body.rotate_degrees,
        crop=body.crop,
        watermark_text=body.watermark_text,
        overlay_text=body.overlay_text,
        generation_id=body.generation_id,
    )
    await db.execute(
        "UPDATE generations SET output_path = ? WHERE id = ?",
        (str(out), body.generation_id),
    )
    return {"output_path": str(out)}


# --- Settings ---
_SECRET_SETTING_KEYS = frozenset(
    {
        "openai_api_key",
        "anthropic_api_key",
        "gemini_api_key",
        "google_client_secret",
        "google_refresh_token",
    }
)


@app.get("/api/settings", response_model=list[SettingItem])
async def list_settings() -> list[SettingItem]:
    rows = await db.fetchall("SELECT key, value FROM settings ORDER BY key")
    out: list[SettingItem] = []
    for r in rows:
        key = str(r["key"])
        value = str(r["value"])
        if key in _SECRET_SETTING_KEYS and value:
            value = "__set__"
        out.append(SettingItem(key=key, value=value))
    return out


@app.put("/api/settings", response_model=SettingItem)
async def put_setting(body: SettingItem) -> SettingItem:
    # UI may send the masked sentinel — never persist it over a real secret.
    if body.key in _SECRET_SETTING_KEYS and body.value in {"", "__set__"}:
        existing = await db.get_setting(body.key)
        if existing:
            return SettingItem(key=body.key, value="__set__")
        raise HTTPException(400, f"{body.key} is empty")
    await db.set_setting(body.key, body.value)
    if body.key in _SECRET_SETTING_KEYS:
        return SettingItem(key=body.key, value="__set__")
    return body


@app.post("/api/system/reset")
async def full_reset(body: ResetRequest) -> dict[str, Any]:
    """Wipe local DB/media/uploads/vault. Does not touch ComfyUI or hfModels."""
    global queue, schedules, vault
    if body.confirm != "RESET":
        raise HTTPException(
            400,
            'Confirmation failed. Send {"confirm":"RESET"} to proceed.',
        )

    q = _require_queue()
    cleared = q.clear()
    await q.stop()
    if vault is not None:
        vault.lock()
    if schedules is not None:
        schedules.due_reminders.clear()
        schedules.shutdown()

    await db.close()
    report = reset_app_data(settings, include_app_models=body.include_app_models)
    report["queue_cleared"] = cleared

    await db.connect()
    # Bust client/WKWebView caches that key on reused paths like /media/generations/1.png
    media_epoch = str(int(time.time()))
    await db.set_setting("media_epoch", media_epoch)
    report["media_epoch"] = media_epoch
    vault = VaultService(db)
    queue = QueueWorker(db, vault=vault)
    schedules = ScheduleService(db)
    await queue.start()
    schedules.start()
    logger.warning("Full local reset completed: %s", report)
    return {"status": "reset", **report}


# --- Schedules ---
@app.get("/api/schedules", response_model=list[Schedule])
async def list_schedules() -> list[Schedule]:
    rows = await db.fetchall("SELECT * FROM schedules ORDER BY id DESC")
    result: list[Schedule] = []
    for r in rows:
        scenes = None
        if r["scene_suggestions"]:
            import json

            scenes = json.loads(r["scene_suggestions"])
        result.append(
            Schedule(
                id=r["id"],
                influencer_id=r["influencer_id"],
                schedule_time=r["schedule_time"],
                frequency=r["frequency"],
                cron_expression=r["cron_expression"],
                prompt_template=r["prompt_template"],
                scene_suggestions=scenes,
                wardrobe_item_id=r["wardrobe_item_id"],
                is_active=bool(r["is_active"]),
                calendar_event_id=r["calendar_event_id"],
                calendar_provider=r["calendar_provider"],
                last_triggered=r["last_triggered"],
                next_trigger=r["next_trigger"],
                created_at=r["created_at"],
            )
        )
    return result


@app.post("/api/schedules", response_model=Schedule)
async def create_schedule(body: ScheduleCreate) -> Schedule:
    from datetime import datetime, timezone

    svc = _require_schedules()
    now = datetime.now(timezone.utc).astimezone()
    next_dt = svc._compute_next(body.schedule_time, body.frequency, now)
    cur = await db.execute(
        """
        INSERT INTO schedules(
            influencer_id, schedule_time, frequency, cron_expression, prompt_template,
            scene_suggestions, wardrobe_item_id, calendar_provider, next_trigger, is_active
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            body.influencer_id,
            body.schedule_time,
            body.frequency,
            body.cron_expression,
            body.prompt_template,
            svc.dumps_scenes(body.scene_suggestions),
            body.wardrobe_item_id,
            body.calendar_provider,
            next_dt.isoformat(sep=" ", timespec="seconds"),
        ),
    )
    sid = cur.lastrowid
    assert sid is not None
    return Schedule(
        id=int(sid),
        **body.model_dump(),
        is_active=True,
        next_trigger=next_dt.isoformat(sep=" ", timespec="seconds"),
    )


@app.patch("/api/schedules/{schedule_id}", response_model=Schedule)
async def patch_schedule(schedule_id: int, body: SchedulePatch) -> Schedule:
    row = await db.fetchone("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
    if not row:
        raise HTTPException(404, "Schedule not found")
    if body.is_active is not None:
        await db.execute(
            "UPDATE schedules SET is_active = ? WHERE id = ?",
            (1 if body.is_active else 0, schedule_id),
        )
    rows = await list_schedules()
    for s in rows:
        if s.id == schedule_id:
            return s
    raise HTTPException(404, "Schedule not found")


@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int) -> dict[str, str]:
    row = await db.fetchone("SELECT id FROM schedules WHERE id = ?", (schedule_id,))
    if not row:
        raise HTTPException(404, "Schedule not found")
    await db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    return {"status": "deleted"}


@app.get("/api/schedules/reminders")
async def schedule_reminders() -> dict[str, Any]:
    return {"reminders": _require_schedules().pop_reminders()}


async def _influencer_names() -> dict[int, str]:
    rows = await db.fetchall("SELECT id, name FROM influencers")
    return {int(r["id"]): str(r["name"]) for r in rows}


@app.get("/api/schedules/export.ics")
async def export_schedules_ics() -> Response:
    """Download all active schedules as an .ics for Google/Apple Calendar import."""
    rows = await db.fetchall("SELECT * FROM schedules WHERE is_active = 1 ORDER BY id ASC")
    ics = build_calendar(list(rows), names=await _influencer_names())
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="influencerforge-schedules.ics"'},
    )


@app.get("/api/schedules/{schedule_id}/export.ics")
async def export_schedule_ics(schedule_id: int) -> Response:
    row = await db.fetchone("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
    if not row:
        raise HTTPException(404, "Schedule not found")
    ics = build_calendar([row], names=await _influencer_names())
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="influencerforge-schedule-{schedule_id}.ics"'
        },
    )


def _google_redirect_uri() -> str:
    return f"http://127.0.0.1:{settings.port}/api/schedules/google/callback"


@app.get("/api/schedules/google/auth-url")
async def google_calendar_auth_url() -> dict[str, str]:
    client_id = await db.get_setting("google_client_id")
    if not client_id:
        raise HTTPException(
            400,
            "Set google_client_id (and secret) under Settings → Google Calendar first.",
        )
    url = calendar_sync.google_auth_url(client_id, redirect_uri=_google_redirect_uri())
    return {"url": url, "redirect_uri": _google_redirect_uri()}


@app.get("/api/schedules/google/callback")
async def google_calendar_callback(code: str = "", error: str = "") -> Response:
    if error:
        return Response(
            content=f"<html><body><p>Google auth error: {error}</p></body></html>",
            media_type="text/html",
        )
    if not code.strip():
        raise HTTPException(400, "Missing OAuth code")
    client_id = await db.get_setting("google_client_id")
    client_secret = await db.get_setting("google_client_secret")
    if not client_id or not client_secret:
        raise HTTPException(400, "Google client id/secret not configured")
    try:
        tokens = calendar_sync.exchange_code_for_tokens(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=_google_redirect_uri(),
        )
    except Exception as exc:
        raise HTTPException(400, f"Token exchange failed: {exc}") from exc
    if tokens.get("refresh_token"):
        await db.set_setting("google_refresh_token", tokens["refresh_token"])
    html = (
        "<html><body style='font-family:system-ui;padding:2rem'>"
        "<h1>Google Calendar connected</h1>"
        "<p>You can close this tab and return to InfluencerForge → Scheduler → Sync to Google.</p>"
        "</body></html>"
    )
    return Response(content=html, media_type="text/html")


@app.post("/api/schedules/google/exchange")
async def google_calendar_exchange(body: GoogleCodeExchange) -> dict[str, str]:
    """Paste-code fallback when the browser redirect flow is unavailable."""
    client_id = await db.get_setting("google_client_id")
    client_secret = await db.get_setting("google_client_secret")
    if not client_id or not client_secret:
        raise HTTPException(400, "Google client id/secret not configured")
    redirect = body.redirect_uri or _google_redirect_uri()
    try:
        tokens = calendar_sync.exchange_code_for_tokens(
            client_id=client_id,
            client_secret=client_secret,
            code=body.code,
            redirect_uri=redirect,
        )
    except Exception as exc:
        raise HTTPException(400, f"Token exchange failed: {exc}") from exc
    if tokens.get("refresh_token"):
        await db.set_setting("google_refresh_token", tokens["refresh_token"])
    return {"status": "connected", "has_refresh_token": "1" if tokens.get("refresh_token") else "0"}


@app.post("/api/schedules/sync-google")
async def sync_schedules_google() -> dict[str, Any]:
    client_id = await db.get_setting("google_client_id")
    client_secret = await db.get_setting("google_client_secret")
    refresh = await db.get_setting("google_refresh_token")
    if not client_id or not client_secret or not refresh:
        raise HTTPException(
            400,
            "Google Calendar not connected. Add client id/secret in Settings, then Connect Google.",
        )
    try:
        access = calendar_sync.refresh_access_token(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh,
        )
    except Exception as exc:
        raise HTTPException(400, f"Google token refresh failed: {exc}") from exc

    rows = await db.fetchall("SELECT * FROM schedules WHERE is_active = 1 ORDER BY id ASC")
    names = await _influencer_names()
    synced = 0
    errors: list[str] = []
    for row in rows:
        schedule = dict(row)
        try:
            event_id = calendar_sync.upsert_schedule_event(
                access_token=access,
                schedule=schedule,
                influencer_name=names.get(int(schedule["influencer_id"]), "Influencer"),
            )
            await db.execute(
                """
                UPDATE schedules
                SET calendar_event_id = ?, calendar_provider = ?
                WHERE id = ?
                """,
                (event_id, "google", int(schedule["id"])),
            )
            synced += 1
        except Exception as exc:
            errors.append(f"schedule {schedule.get('id')}: {exc}")
    return {"status": "ok", "synced": synced, "errors": errors}


# --- Vault ---
@app.get("/api/vault/status")
async def vault_status() -> dict[str, Any]:
    v = _require_vault()
    pending = await v.count_pending_nsfw() if await v.is_configured() else 0
    return {
        "configured": await v.is_configured(),
        "unlocked": v.unlocked,
        "pending_nsfw": pending,
    }


@app.post("/api/vault/setup")
async def vault_setup(body: VaultSetup) -> dict[str, str]:
    await _require_vault().setup(body.pin)
    return {"status": "configured"}


@app.post("/api/vault/unlock")
async def vault_unlock(body: VaultUnlock) -> dict[str, Any]:
    v = _require_vault()
    ok = await v.unlock(body.pin)
    if not ok:
        raise HTTPException(401, "Invalid PIN")
    pending = await v.count_pending_nsfw()
    return {"unlocked": True, "pending_nsfw": pending}


@app.post("/api/vault/lock")
async def vault_lock() -> dict[str, str]:
    _require_vault().lock()
    return {"status": "locked"}


@app.post("/api/vault/end-view")
async def vault_end_view() -> dict[str, str]:
    """Clear decrypted reveal cache after closing a lightbox (PIN required again next open)."""
    _require_vault().end_view_session()
    return {"status": "view_ended"}


@app.get("/api/vault/generations")
async def list_vault_generations() -> list[dict[str, Any]]:
    return await _require_vault().list_vaulted()


@app.post("/api/vault/generations/pending")
async def vault_pending_nsfw() -> dict[str, Any]:
    try:
        return await _require_vault().vault_pending_nsfw()
    except RuntimeError as exc:
        raise HTTPException(401, str(exc)) from exc


@app.post("/api/vault/generations/{generation_id}")
async def vault_generation(generation_id: int) -> dict[str, str]:
    try:
        return await _require_vault().vault_generation(generation_id)
    except RuntimeError as exc:
        raise HTTPException(401, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/vault/generations/{generation_id}/image")
async def reveal_vault_generation(generation_id: int) -> FileResponse:
    try:
        path = await _require_vault().reveal_generation(generation_id)
    except RuntimeError as exc:
        raise HTTPException(401, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return FileResponse(
        path,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


# Media — dynamic FileResponse so IFORGE_DATA_DIR / tests can retarget settings.media_dir
_MEDIA_SUBDIRS = frozenset({"generations", "thumbnails", "uploads"})
_NO_STORE = {"Cache-Control": "no-store"}


@app.get("/media/{subdir}/{filename}")
async def serve_media(subdir: str, filename: str) -> FileResponse:
    """Serve generation / thumbnail / upload images for the desktop UI."""
    if subdir not in _MEDIA_SUBDIRS:
        raise HTTPException(404, "Unknown media folder")
    # Block path traversal in the filename segment.
    if Path(filename).name != filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    settings.ensure_directories()
    path = (settings.media_dir / subdir / filename).resolve()
    root = settings.media_dir.resolve()
    if not str(path).startswith(str(root)) or not path.is_file():
        raise HTTPException(404, "File not found")
    suffix = path.suffix.lower()
    media_type = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix)
    return FileResponse(path, media_type=media_type, headers=_NO_STORE)


def main() -> None:
    uvicorn.run(
        "forge_python.orchestrator:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
