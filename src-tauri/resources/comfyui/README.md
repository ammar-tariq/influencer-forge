# ComfyUI bundle location

This folder is intentionally empty in git. Clone ComfyUI locally (ignored by `.gitignore`):

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
