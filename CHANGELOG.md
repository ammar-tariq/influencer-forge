# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Video: FaceID on by default at 12×384×640 (identity/gender); longer ~2s clip; don’t inject nude over clothed NSFW; queue “processing” only while a job runs; video autoplay muted.
- Video playback: require real `.mp4` (don’t force `<video>` on stub PNGs); serve `/media` with `video/mp4`; clear error when VHS lacks ffmpeg.
- AnimateDiff Gen2 video workflow: FaceID on checkpoint `MODEL`, then `ADE_UseEvolvedSampling` (fixes M_MODELS vs MODEL 400).
- Under-18 looks prompts: girl/boy phrasing, keep selected height, drop adult breast/hip/butt tokens, age-accurate proportion cues + negatives.
- FaceID / AnimateDiff workflows: set InsightFace `model_name` to `buffalo_l` (ComfyUI 400: required input missing).
- Full reset / delete confirmations no longer use `window.confirm` (silent no-op in macOS Tauri); in-app confirm + cache clear after reset.

### Changed

- Prompt override contract: wardrobe XOR dressing; strip clothing from notes when wardrobe is set; block nude+wardrobe; stop rogue `nude` inject; `identity_explore` skips face refs on setup batches; create-post keeps face+body fixed (hybrid looks).
- System monitor cards (CPU/RAM/queue, ComfyUI, pause/resume) live under Settings; `/monitor` redirects there.
- Privacy vault is a sidebar switch (PIN on enable) instead of a full `/vault` page; vaulted NSFW hides when off and shows blur teasers in Library/profile when on.
- Influencer cards open the profile on click; removed Open profile / Create post / Their posts button clusters and face-lock status badges.
- Profile: Back control, Delete (hard-delete + media) instead of Archive; Unlock face / Library clutter removed; wardrobe assign section added.
- Wardrobe is part of the create-post flow (assigned outfits inject consistent keywords); Edit photo replaced by Edit posts (replace generation in place).

### Added

- Delete post from Library / profile lightbox (`DELETE /api/generations/{id}` removes DB row + media/vault files).
- Batch face options on create/setup: `POST /api/generations/batch` queues 2–8 shots (wizard + profile default to 4) so users can pick a face to lock.
- Influencers list + detail screens (`/influencers`, `/influencers/:id`) with personality/looks, per-influencer generations, archive, and Library deep links (`?influencer=`).
- Face-lock setup on the profile: identity prompt retries, Face Seed upload, `POST /api/influencers/{id}/face-lock` (explicit lock; no longer auto-locks on first SFW).
- `PATCH /api/personalities/{id}` and `PATCH /api/looks/{id}` with profile edit UI; `face_lock_stale` warning when hair/eyes/ethnicity change while locked.
- IP-Adapter FaceID Plus SDXL workflow (`image_ipadapter_faceid.json`) with img2img fallback; readiness + bootstrap URL entries for FaceID weights.
- Real AnimateDiff video workflow (`video_animate.json`) producing `.mp4` (optional FaceID on video); Library/Generate `<video>` preview.
- `scripts/assemble-portable-python.sh` + Tauri bundle resources for portable Python / frozen `forge-python` (models still downloaded separately).
- `GET /api/influencers/{id}` (`InfluencerDetail`) and `POST /api/influencers/{id}/archive`; list rows include `generation_count`.
- ComfyUI client queue/history/view path with stub fallback and `/api/comfyui/status`.
- Resumable model bootstrap downloader driven by `resources/bootstrap/models.json`.
- Face Seed fingerprint extraction (`face_seed.py`) stored on Looks rows.
- SDXL/AnimateDiff workflow graphs under `src-tauri/resources/workflows/`.
- Monitor UI ComfyUI health panel.
- `/api/readiness` checklist + Dashboard/Generate UI explaining stub vs real mode.
- `require_real` generation flag and `IFORGE_ALLOW_STUB_FALLBACK` to stop silent placeholders.
- `docs/setup/REAL_GENERATION.md` — path from CRUD to first real SDXL image.
- Full local reset via `POST /api/system/reset` and Settings UI (wipes DB/media/vault; keeps hfModels/ComfyUI).

## [0.1.0] - 2026-08-10

### Added

- Initial open-source scaffold: Tauri v2 shell, React UI, FastAPI orchestrator.
- SQLite schema for influencers, wardrobe, generations, schedules, settings, vault.
- Stub image/video generation queue for local development without multi‑GB models.
- Privacy vault, scheduler reminders, system monitor, post-production helpers.
- CI lint/test workflows and desktop build workflow stub.
- Cursor/AGENTS documentation for contributors using Cursor.
