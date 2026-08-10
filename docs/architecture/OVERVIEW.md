# Architecture overview

```text
React UI  --HTTP-->  FastAPI :8765  --> SQLite
                         |
                         +--> QueueWorker --> StubGenerator (Phase 1)
                         |                 \-> ComfyUI :8188 (Phase 2+, optional)
                         +--> Scheduler / Vault / Monitor
Tauri (Rust) spawns/kills Python orchestrator; system tray pause/resume/quit
```

## Data directory

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/InfluencerForge/` |
| Windows | `%APPDATA%/InfluencerForge/` |
| Linux | `~/.config/InfluencerForge/` |

Contains `data.db`, `media/`, `models/`, `vault/`, `uploads/`.

## Environment flags

| Variable | Default | Meaning |
|----------|---------|---------|
| `IFORGE_DATA_DIR` | OS default | Override data root |
| `IFORGE_PORT` | `8765` | API port |
| `IFORGE_ENABLE_COMFYUI` | `0` | Spawn/use ComfyUI when available; stub fallback otherwise |
| `IFORGE_ENABLE_MODEL_DOWNLOADS` | `0` | Download assets from `resources/bootstrap/models.json` |
| `IFORGE_COMFYUI_ROOT` | `src-tauri/resources/comfyui/ComfyUI` | Path to ComfyUI `main.py` |
| `IFORGE_MODEL_MANIFEST` | `resources/bootstrap/models.json` | Download manifest |
| `IFORGE_PYTHON_ROOT` | auto | Override forge-python root |

### ComfyUI flow

1. Queue worker calls `ComfyUIClient.generate`
2. If enabled, client may spawn ComfyUI and wait for `/system_stats`
3. Workflow JSON under `src-tauri/resources/workflows/` is injected (prompt/seed/size)
4. Prompt is posted to `/prompt`, history polled, image fetched via `/view`
5. On any failure, Pillow stub generator keeps the product path usable
