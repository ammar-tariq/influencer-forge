# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- ComfyUI client queue/history/view path with stub fallback and `/api/comfyui/status`.
- Resumable model bootstrap downloader driven by `resources/bootstrap/models.json`.
- Face Seed fingerprint extraction (`face_seed.py`) stored on Looks rows.
- SDXL/AnimateDiff workflow graphs under `src-tauri/resources/workflows/`.
- Monitor UI ComfyUI health panel.
- `/api/readiness` checklist + Dashboard/Generate UI explaining stub vs real mode.
- `require_real` generation flag and `IFORGE_ALLOW_STUB_FALLBACK` to stop silent placeholders.
- `docs/setup/REAL_GENERATION.md` — path from CRUD to first real SDXL image.

## [0.1.0] - 2026-08-10

### Added

- Initial open-source scaffold: Tauri v2 shell, React UI, FastAPI orchestrator.
- SQLite schema for influencers, wardrobe, generations, schedules, settings, vault.
- Stub image/video generation queue for local development without multi‑GB models.
- Privacy vault, scheduler reminders, system monitor, post-production helpers.
- CI lint/test workflows and desktop build workflow stub.
- Cursor/AGENTS documentation for contributors using Cursor.
