# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Wizard height option **Very short (under 4'11" / 150cm)** below Petite.
- Docs/readiness/install script point users to download the recommended SDXL NSFW LoRA (Muapi woman033) — weights stay out of git.
- Wav2Lip talking-head path (`scripts/install-wav2lip.sh` + ComfyUI node) with ffmpeg still+audio fallback.
- Google Calendar OAuth sync (`Settings` client id/secret → Connect → Scheduler Sync to Google); Apple remains ICS export.
- Bootstrap manifest v2: optional SDXL base + Wav2Lip gan URLs; downloads mirror into ComfyUI `models/`.
- System monitor GPU/VRAM via `nvidia-smi` (Apple Silicon labeled MPS); NSFW LoRA auto-inject; InstantID readiness item.
- `scripts/install-instantid.sh` + `scripts/install-nsfw-lora.sh`; InstantID readiness requires node + InstantX weights.
- Library drag-to-crop preview; cross-platform release checklist (`docs/setup/RELEASE_VALIDATION.md`).
- Talking-head workflow (`lip_sync`): audio upload + ffmpeg face/audio mux to `.mp4`.
- Local GGUF scene enrich (optional `llama-cpp-python` + `models/llm/*.gguf` or Settings path); Llama 3.2 1B bootstrap entry.
- Scheduler ICS export (`.ics`) for Google/Apple Calendar import — all schedules or one.
- System tray Pause/Resume queue wired to orchestrator via Tauri events.
- Claude (Haiku) and Gemini (Flash) scene enrich alongside OpenAI; template fallback on failure.
- Library lightbox crop: 10%/20% margin presets + numeric x1,y1,x2,y2.
- Scheduler: pause/resume/delete, next_trigger on create, reminder → Create post deep-link (Dashboard + Scheduler).
- OpenAI scene enrich when Settings → LLM provider is OpenAI (template fallback on failure).
- Library lightbox image edits: rotate ±90, watermark, overlay via `POST /api/post-process`.
- `npm run package` = assemble portable Python + `tauri build`.

### Fixed

- Video: enqueue preflight for AnimateDiff; require ffmpeg; Face Seed + FaceID fail-closed unless `IFORGE_VIDEO_FACEID=0`; no stub for video/lip_sync.
- Face Seed jobs refuse plain txt2img/stub when FaceID and img2img are unavailable (no invented face).
- Face Seed create/regenerate: looks text is body-only (no ethnicity/hair/age fighting the reference); Library regenerate defaults to face-lock.
- Video: FaceID on by default at 12×384×640 (identity/gender); longer ~2s clip; don’t inject nude over clothed NSFW; queue “processing” only while a job runs; video autoplay muted.
- Video playback: require real `.mp4` (don’t force `<video>` on stub PNGs); serve `/media` with `video/mp4`; clear error when VHS lacks ffmpeg.
- AnimateDiff Gen2 video workflow: FaceID on checkpoint `MODEL`, then `ADE_UseEvolvedSampling` (fixes M_MODELS vs MODEL 400).
- Under-18 looks prompts: girl/boy phrasing, keep selected height, drop adult breast/hip/butt tokens, age-accurate proportion cues + negatives.
- FaceID / AnimateDiff workflows: set InsightFace `model_name` to `buffalo_l` (ComfyUI 400: required input missing).
- Full reset / delete confirmations no longer use `window.confirm` (silent no-op in macOS Tauri); in-app confirm + cache clear after reset.

### Changed

- NSFW: personality age rating no longer gates explicit jobs (Family/Teen/Adult/18+ allowed); looks age must still be 18+. Generate still defaults NSFW on for Adult/18+.
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
