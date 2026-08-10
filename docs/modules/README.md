# Module documentation index

| Module | Code | Notes |
|--------|------|-------|
| Orchestrator API | `forge-python/src/forge_python/orchestrator.py` | FastAPI routes |
| Database | `forge-python/src/forge_python/db.py` | Full schema from spec |
| Queue + stub/Comfy | `queue_worker.py`, `stub_generator.py`, `comfyui_client.py` | Concurrency 1; Comfy prompt/history/view |
| Face Seed | `face_seed.py` | Local fingerprint until InstantID |
| Model bootstrap | `model_downloader.py` + `resources/bootstrap/models.json` | Resumable downloads when enabled |
| LLM expand | `llm_manager.py` | Template-first |
| Vault | `vault.py` | Argon2id + AES-GCM |
| Scheduler | `scheduler.py` | APScheduler reminders |
| System monitor | `system_monitor.py` | psutil |
| Post | `post_processing.py` | Pillow edits |
| Bootstrap | `model_downloader.py` | No HF in Phase 1 |
| Tauri process mgr | `src-tauri/src/process_manager.rs` | Spawn system/venv Python |
| System tray | `src-tauri/src/system_tray.rs` | Pause/resume/quit |
| UI pages | `src/pages/*` | Splash → studio surfaces |

Workflow JSON stubs: `src-tauri/resources/workflows/`.
