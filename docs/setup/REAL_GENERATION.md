# When does InfluencerForge stop being “just CRUD”?

**Answer:** when Dashboard readiness is `mode: real` and History shows `model_used` other than `stub`.

## Checklist

| Step | Command / action |
|------|------------------|
| 1. Clone ComfyUI | `git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git src-tauri/resources/comfyui/ComfyUI` |
| 2. Install ComfyUI Python deps | follow upstream ComfyUI README inside that folder |
| 3. Drop SDXL checkpoint | `.../ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors` |
| 4. Enable flag | `export IFORGE_ENABLE_COMFYUI=1` |
| 5. Launch | `npm run tauri dev` or `uv run forge-orchestrator` |
| 6. Verify API | `curl localhost:8765/api/readiness` → `"real_ready": true` |

## Stub vs real

- Default: stub placeholders allowed (`IFORGE_ALLOW_STUB_FALLBACK=1`) so UI/queue can be developed offline.
- Generate page toggle **Require real ComfyUI output** sets `require_real: true` and fails the job instead of painting a fake PNG.
- Set `IFORGE_ALLOW_STUB_FALLBACK=0` globally to force real-only.

## Dev: app “crashes” mid-generation

If `npm run tauri dev` logs `File src-tauri/resources/comfyui/ComfyUI/temp changed. Rebuilding application…`, the desktop process is being **hot-reloaded**, not randomly crashing. ComfyUI writes into `temp/` while sampling; Tauri’s watcher used to treat that as a Rust source change.

Fix: `src-tauri/.taurignore` ignores `resources/comfyui/`. Restart `tauri dev` after pulling that file. Fallback: `npm run tauri dev -- --no-watch`.

## GPU note

SDXL needs a capable GPU (or a slow CPU run). Without hardware, readiness may be green but jobs will be slow or OOM — that is a runtime issue, not CRUD.

## Apple Silicon

Ignore `comfy-aimdo unsupported operating system: Darwin` — that is NVIDIA-only.
A healthy Mac log includes `Device: mps` and `To see the GUI go to: http://127.0.0.1:8188`.

Existing single-file checkpoints (e.g. `/Volumes/external/hfModels/RealVisXL_V5.0/…`) can be symlinked into
`ComfyUI/models/checkpoints/` or discovered via `IFORGE_EXTRA_MODEL_DIRS`.
