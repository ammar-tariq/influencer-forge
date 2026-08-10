# ComfyUI bundle location

This folder is intentionally empty in git. Clone ComfyUI locally (ignored by `.gitignore`).

**Dev tip:** `src-tauri/.taurignore` excludes this tree from the Tauri file watcher.
Without that, ComfyUI writing `temp/` during a run triggers `File …/temp changed. Rebuilding application…`, which restarts the desktop app and aborts in-flight jobs.

## Clone

```bash
cd src-tauri/resources/comfyui
git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git ComfyUI
```

## Make real generation work

1. **Checkpoint** — put a single-file SDXL `.safetensors` in:

   `ComfyUI/models/checkpoints/`

   Or keep models elsewhere (e.g. `/Volumes/external/hfModels`) and symlink / set
   `IFORGE_EXTRA_MODEL_DIRS`. This machine uses:

   `RealVisXL_V5.0_fp16.safetensors` → linked from `/Volumes/external/hfModels/RealVisXL_V5.0/`

   Diffusers folders (like `ideogram/`) are **not** usable by the current CheckpointLoader workflow.

2. **Enable** before launching:

```bash
export IFORGE_ENABLE_COMFYUI=1
# optional: refuse placeholders
export IFORGE_ALLOW_STUB_FALLBACK=0
npm run tauri dev
```

3. Open the app Dashboard — the readiness checklist should turn green.

4. Generate an image. History should show a real SDXL output (`model_used` ≠ `stub`).

## Face Seed note

Uploading a Face Seed stores a local fingerprint today and annotates the prompt.
Full InstantID/IP-Adapter node wiring is the next milestone after SDXL txt2img works.

## Apple Silicon / macOS notes

These log lines are **normal and harmless** on Mac:

```text
[WARNING] Could not autodetect AIMDO implementation, assuming Nvidia
[INFO] comfy-aimdo unsupported operating system: Darwin
```

AIMDO is a Windows/Linux NVIDIA path. On Apple, ComfyUI should report:

```text
Device: mps
To see the GUI go to: http://127.0.0.1:8188
```

Start manually if needed:

```bash
cd src-tauri/resources/comfyui/ComfyUI
.venv/bin/python main.py --listen 127.0.0.1 --port 8188 --force-fp16
```
