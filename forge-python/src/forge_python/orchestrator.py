"""FastAPI orchestrator entrypoint for InfluencerForge."""

from __future__ import annotations

import logging
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from forge_python import __version__
from forge_python.config import settings
from forge_python.db import Database, body_from_json, body_to_json, traits_from_json, traits_to_json
from forge_python.face_seed import extract_face_embedding
from forge_python.llm_manager import (
    build_looks_prompt,
    build_system_prompt,
    expand_prompt,
    prompt_implies_nsfw,
    resolve_negative_prompt,
    smart_daily_suggestions,
)
from forge_python.model_downloader import ModelDownloader
from forge_python.models import (
    BootstrapStatus,
    FaceLockRequest,
    Generation,
    GenerationCreate,
    HealthResponse,
    Influencer,
    InfluencerCreate,
    InfluencerDetail,
    Looks,
    LooksCreate,
    Personality,
    PersonalityCreate,
    PostProcessRequest,
    QueueStatus,
    ResetRequest,
    Schedule,
    ScheduleCreate,
    SettingItem,
    SystemStats,
    VaultSetup,
    VaultUnlock,
    WardrobeCreate,
    WardrobeItem,
)
from forge_python.post_processing import process_image
from forge_python.queue_worker import QueueWorker
from forge_python.readiness import collect_readiness
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
    return HealthResponse(
        status="ok",
        version=__version__,
        data_dir=str(settings.data_dir),
        api="influencerforge",
        features=["readiness", "reset", "comfyui", "influencer_detail"],
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
        hair_color=body.hair_color,
        hair_style=body.hair_style,
        eye_color=body.eye_color,
        style=body.style,
        gender=body.gender,
        body=body.body,
    )
    cur = await db.execute(
        """
        INSERT INTO looks(name, age, gender, ethnicity, hair_color, hair_style, eye_color, style,
                          body_json, base_prompt, reference_image_path)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.name,
            body.age,
            body.gender,
            body.ethnicity,
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


def _looks_from_row(r: dict[str, Any]) -> Looks:
    return Looks(
        id=r["id"],
        name=r["name"],
        age=r["age"],
        gender=r.get("gender") or "Female",
        ethnicity=r["ethnicity"],
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


@app.post("/api/influencers/{influencer_id}/wardrobe/{item_id}")
async def assign_wardrobe(influencer_id: int, item_id: int) -> dict[str, str]:
    await db.execute(
        """
        INSERT OR IGNORE INTO influencer_wardrobe(influencer_id, wardrobe_item_id)
        VALUES(?, ?)
        """,
        (influencer_id, item_id),
    )
    return {"status": "assigned"}


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


@app.post("/api/generations", response_model=Generation)
async def create_generation(body: GenerationCreate) -> Generation:
    wardrobe_keywords = None
    if body.wardrobe_item_id:
        item = await db.fetchone(
            "SELECT prompt_keywords FROM wardrobe_items WHERE id = ?",
            (body.wardrobe_item_id,),
        )
        if item:
            wardrobe_keywords = item["prompt_keywords"]
    influencer = await db.fetchone("SELECT * FROM influencers WHERE id = ?", (body.influencer_id,))
    if not influencer:
        raise HTTPException(400, "Invalid influencer_id")
    personality = await db.fetchone(
        "SELECT * FROM personalities WHERE id = ?",
        (influencer["personality_id"],),
    )
    looks = await db.fetchone("SELECT * FROM looks WHERE id = ?", (influencer["looks_id"],))
    age_rating = (personality or {}).get("age_rating") or "Family"
    # Toggle or explicit prompt language → NSFW path (clothing negatives + adult framing).
    # Age rating alone does not force NSFW so studio headshots stay SFW.
    is_nsfw = bool(body.is_nsfw or prompt_implies_nsfw(body.user_prompt))
    if is_nsfw and age_rating in ("Family", "Teen"):
        raise HTTPException(
            400,
            "Explicit / NSFW generation requires an Adult or 18+ age rating on the influencer.",
        )
    looks_prompt = build_looks_prompt(
        age=(looks or {}).get("age"),
        ethnicity=(looks or {}).get("ethnicity"),
        hair_color=(looks or {}).get("hair_color"),
        hair_style=(looks or {}).get("hair_style"),
        eye_color=(looks or {}).get("eye_color"),
        style=(looks or {}).get("style"),
        gender=(looks or {}).get("gender"),
        body=body_from_json((looks or {}).get("body_json")),
        for_nsfw=is_nsfw,
    )
    expanded = expand_prompt(
        body.user_prompt,
        influencer_name=influencer["name"],
        looks_prompt=looks_prompt or (looks or {}).get("base_prompt") or "",
        wardrobe_keywords=None if is_nsfw else wardrobe_keywords,
        system_prompt=(personality or {}).get("system_prompt"),
        is_nsfw=is_nsfw,
    )
    negative = resolve_negative_prompt(is_nsfw=is_nsfw)
    cur = await db.execute(
        """
        INSERT INTO generations(
            influencer_id, user_prompt, expanded_prompt, negative_prompt,
            workflow_type, model_used, llm_used,
            aspect_ratio, seed, steps, cfg_scale, is_nsfw, status
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
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
            body.seed,
            body.steps,
            body.cfg_scale,
            int(is_nsfw),
        ),
    )
    gid = cur.lastrowid
    assert gid is not None
    await _require_queue().enqueue(int(gid), require_real=body.require_real)
    row = await db.fetchone("SELECT * FROM generations WHERE id = ?", (gid,))
    assert row
    return Generation(**row)


@app.post("/api/generations/{generation_id}/regenerate", response_model=Generation)
async def regenerate(generation_id: int, require_real: bool = False) -> Generation:
    parent = await db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
    if not parent:
        raise HTTPException(404, "Not found")
    cur = await db.execute(
        """
        INSERT INTO generations(
            influencer_id, parent_generation_id, user_prompt, expanded_prompt, negative_prompt,
            workflow_type, model_used, llm_used, aspect_ratio, seed, steps, cfg_scale, is_nsfw, status
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (
            parent["influencer_id"],
            parent["id"],
            parent["user_prompt"],
            parent["expanded_prompt"],
            parent["negative_prompt"],
            parent["workflow_type"],
            parent["model_used"],
            parent["llm_used"],
            parent["aspect_ratio"],
            parent["seed"],
            parent["steps"],
            parent["cfg_scale"],
            parent["is_nsfw"],
        ),
    )
    gid = cur.lastrowid
    assert gid is not None
    await _require_queue().enqueue(int(gid), require_real=require_real)
    row = await db.fetchone("SELECT * FROM generations WHERE id = ?", (gid,))
    assert row
    return Generation(**row)


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
@app.get("/api/settings", response_model=list[SettingItem])
async def list_settings() -> list[SettingItem]:
    rows = await db.fetchall("SELECT key, value FROM settings ORDER BY key")
    return [SettingItem(key=r["key"], value=r["value"]) for r in rows]


@app.put("/api/settings", response_model=SettingItem)
async def put_setting(body: SettingItem) -> SettingItem:
    await db.set_setting(body.key, body.value)
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
    svc = _require_schedules()
    cur = await db.execute(
        """
        INSERT INTO schedules(
            influencer_id, schedule_time, frequency, cron_expression, prompt_template,
            scene_suggestions, wardrobe_item_id, calendar_provider
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
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
        ),
    )
    sid = cur.lastrowid
    assert sid is not None
    return Schedule(id=int(sid), **body.model_dump())


@app.get("/api/schedules/reminders")
async def schedule_reminders() -> dict[str, Any]:
    return {"reminders": _require_schedules().pop_reminders()}


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
async def vault_unlock(body: VaultUnlock) -> dict[str, bool]:
    ok = await _require_vault().unlock(body.pin)
    if not ok:
        raise HTTPException(401, "Invalid PIN")
    return {"unlocked": True}


@app.post("/api/vault/lock")
async def vault_lock() -> dict[str, str]:
    _require_vault().lock()
    return {"status": "locked"}


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
    return FileResponse(path, media_type="image/png")


# Media — dynamic FileResponse so IFORGE_DATA_DIR / tests can retarget settings.media_dir
_MEDIA_SUBDIRS = frozenset({"generations", "thumbnails", "uploads"})


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
    return FileResponse(path)


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
