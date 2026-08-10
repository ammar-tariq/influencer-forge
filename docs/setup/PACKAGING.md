# Packaging & embedded Python

InfluencerForge ships a **desktop shell + orchestrator**. Multi‑GB diffusion / FaceID / AnimateDiff weights stay **out of git** and out of the installer — users (or first-launch bootstrap) download them into app data / ComfyUI `models/`.

## Development vs release

| | Dev (`npm run tauri dev`) | Release (`tauri build` / CI) |
|--|---------------------------|------------------------------|
| Python | `forge-python/.venv` (preferred) or system `python3` | Bundled `resources/python` from assemble script |
| Orchestrator code | Repo `forge-python/src` | Frozen copy at `resources/forge-python/src` |
| Models | Local ComfyUI / `IFORGE_EXTRA_MODEL_DIRS` | Same — readiness + optional `IFORGE_ENABLE_MODEL_DOWNLOADS=1` |
| Workflows | `src-tauri/resources/workflows/` | Bundled with the app |

Override roots anytime:

- `IFORGE_PYTHON_ROOT` — directory containing `src/forge_python`
- `IFORGE_DATA_DIR` — SQLite + media + vault
- `IFORGE_COMFYUI_ROOT` — ComfyUI install

## Assemble portable Python

```bash
# Requires uv (https://docs.astral.sh/uv/)
chmod +x scripts/assemble-portable-python.sh
./scripts/assemble-portable-python.sh
```

This populates (gitignored):

1. `src-tauri/resources/python/` — relocatable CPython + pip-installed orchestrator deps
2. `src-tauri/resources/forge-python/` — frozen `src/forge_python` package

Then build:

```bash
npm run tauri build
# or rely on .github/workflows/build.yml (runs assemble before tauri-action)
```

`tauri.conf.json` `bundle.resources` includes `python/**` and `forge-python/**`.

## Process manager resolution

Rust `resolve_python()` prefers `resources/python/python` next to the binary, then walks up for the same layout (dev), then PATH.

`forge_python_root()` prefers `IFORGE_PYTHON_ROOT`, then bundled `resources/forge-python`, then the repo `forge-python/` folder.

In release, the child process uses the bundled interpreter + `PYTHONPATH=…/forge-python/src`. In dev, the uv venv wins when present.

## First launch / models

1. Dashboard `/api/readiness` checklist (ComfyUI source, checkpoint, workflows).
2. Optional FaceID / AnimateDiff items stay optional for core `real` mode.
3. Bootstrap URLs live in `src-tauri/resources/bootstrap/models.json` — downloads only when `IFORGE_ENABLE_MODEL_DOWNLOADS=1`.
4. ComfyUI itself is cloned locally under `src-tauri/resources/comfyui/` (dev) or pointed at via `IFORGE_COMFYUI_ROOT` (user install).

## CI

`.github/workflows/build.yml` installs uv, syncs `forge-python`, runs `assemble-portable-python.sh`, then `tauri-action`. Tag pushes (`v*`) and `workflow_dispatch` trigger builds.
