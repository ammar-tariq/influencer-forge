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
| `IFORGE_ENABLE_COMFYUI` | `0` | Prefer ComfyUI when healthy |
| `IFORGE_ENABLE_MODEL_DOWNLOADS` | `0` | Allow HF bootstrap downloads |
| `IFORGE_PYTHON_ROOT` | auto | Override forge-python root |
