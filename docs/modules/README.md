# Module documentation index

| Module | Code | Notes |
|--------|------|-------|
| Orchestrator API | `forge-python/src/forge_python/orchestrator.py` | FastAPI routes |
| Database | `forge-python/src/forge_python/db.py` | Full schema from spec |
| Queue + stub/Comfy | `queue_worker.py`, `stub_generator.py`, `comfyui_client.py` | Concurrency 1; txt2img + img2img face lock |
| Face Seed | `face_seed.py` + `image_img2img.json` | Fingerprint + img2img identity lock (InstantID later) |
| Model bootstrap | `model_downloader.py` + `resources/bootstrap/models.json` | Resumable downloads when enabled |
| Full reset | `reset.py` + `POST /api/system/reset` | Wipes app data; never touches hfModels/ComfyUI |
| LLM expand | `llm_manager.py` | Template-first; OpenAI/Claude/Gemini enrich |
| Vault | `vault.py` | Argon2id + AES-GCM; wipe cleartext; teaser gallery + reveal API |
| Scheduler | `scheduler.py` | APScheduler reminders |
| System monitor | `system_monitor.py` | psutil |
| Post | `post_processing.py` | Pillow edits |
| Bootstrap | `model_downloader.py` | No HF in Phase 1 |
| Tauri process mgr | `src-tauri/src/process_manager.rs` | Spawn system/venv Python |
| System tray | `src-tauri/src/system_tray.rs` | Pause/resume/quit |
| UI pages | `src/pages/*` | Splash → studio surfaces |

Workflow JSON stubs: `src-tauri/resources/workflows/`.
