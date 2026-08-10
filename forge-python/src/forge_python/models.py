"""Pydantic request/response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    data_dir: str
    # Used by the Tauri shell to detect stale orchestrators that only expose /api/health.
    api: str = "influencerforge"
    features: list[str] = Field(default_factory=lambda: ["readiness", "reset", "comfyui"])


class BootstrapStatus(BaseModel):
    ready: bool
    progress: float = Field(ge=0, le=100)
    stage: str
    message: str
    steps: list[dict[str, Any]] = Field(default_factory=list)


class PersonalityCreate(BaseModel):
    name: str
    bio: str | None = None
    traits: dict[str, str] = Field(default_factory=dict)
    niche: str
    age_rating: Literal["Family", "Teen", "Adult", "18+"] = "Family"


class Personality(PersonalityCreate):
    id: int
    system_prompt: str | None = None
    created_at: str | None = None


class LooksCreate(BaseModel):
    name: str
    age: int | None = 25
    ethnicity: str | None = None
    hair_color: str | None = None
    hair_style: str | None = None
    eye_color: str | None = None
    style: str | None = None
    base_prompt: str | None = None
    reference_image_path: str | None = None


class Looks(LooksCreate):
    id: int
    face_embedding: str | None = None
    lora_path: str | None = None
    base_portrait_path: str | None = None
    created_at: str | None = None


class InfluencerCreate(BaseModel):
    personality_id: int
    looks_id: int
    name: str | None = None


class Influencer(BaseModel):
    id: int
    personality_id: int
    looks_id: int
    name: str
    is_active: bool = True
    created_at: str | None = None


class WardrobeCreate(BaseModel):
    name: str
    description: str | None = None
    category: str = "Full Outfit"
    prompt_keywords: str
    preview_image: str | None = None
    is_shared: bool = False


class WardrobeItem(WardrobeCreate):
    id: int
    created_at: str | None = None


class GenerationCreate(BaseModel):
    influencer_id: int
    user_prompt: str
    workflow_type: Literal["image", "video"] = "image"
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    seed: int | None = None
    steps: int = 20
    cfg_scale: float = 7.0
    wardrobe_item_id: int | None = None
    is_nsfw: bool = False
    model_used: str = "stub"
    llm_used: str = "template"
    # When true, fail the job instead of writing a Pillow placeholder.
    require_real: bool = False


class Generation(BaseModel):
    id: int
    influencer_id: int
    parent_generation_id: int | None = None
    user_prompt: str
    expanded_prompt: str
    negative_prompt: str | None = None
    workflow_type: str
    model_used: str
    llm_used: str
    aspect_ratio: str
    seed: int | None = None
    steps: int | None = None
    cfg_scale: float | None = None
    output_path: str | None = None
    output_thumbnail_path: str | None = None
    is_nsfw: bool = False
    is_vaulted: bool = False
    vault_file_path: str | None = None
    teaser_path: str | None = None
    status: str
    error_message: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class ScheduleCreate(BaseModel):
    influencer_id: int
    schedule_time: str
    frequency: Literal["daily", "weekly", "monthly", "custom"] = "daily"
    cron_expression: str | None = None
    prompt_template: str
    scene_suggestions: list[str] | None = None
    wardrobe_item_id: int | None = None
    calendar_provider: Literal["google", "apple"] | None = None


class Schedule(ScheduleCreate):
    id: int
    is_active: bool = True
    calendar_event_id: str | None = None
    last_triggered: str | None = None
    next_trigger: str | None = None
    created_at: str | None = None


class SettingItem(BaseModel):
    key: str
    value: str


class ResetRequest(BaseModel):
    """Destructive reset of local app data. confirm must be exactly RESET."""

    confirm: str
    include_app_models: bool = False


class SystemStats(BaseModel):
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    gpu_name: str | None = None
    gpu_util_percent: float | None = None
    vram_used_gb: float | None = None
    vram_total_gb: float | None = None
    temperature_c: float | None = None
    queue_pending: int = 0
    queue_processing: int = 0


class VaultSetup(BaseModel):
    pin: str = Field(min_length=4, max_length=32)


class VaultUnlock(BaseModel):
    pin: str


class PostProcessRequest(BaseModel):
    generation_id: int
    rotate_degrees: int = 0
    crop: tuple[int, int, int, int] | None = None
    watermark_text: str | None = None
    overlay_text: str | None = None


class QueueStatus(BaseModel):
    pending: int
    processing: int
    paused: bool
