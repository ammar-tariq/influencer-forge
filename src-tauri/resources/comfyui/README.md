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
5. With a Face Seed or base portrait:
   - **IP-Adapter FaceID** when installed → `model_used` = `sdxl-faceid`
   - else **img2img** fallback → `model_used` = `sdxl-img2img`

## IP-Adapter FaceID Plus (stronger identity)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
```

Place weights (not in git):

| File | Typical path |
|------|----------------|
| `ip-adapter-faceid-plusv2_sdxl.bin` | `ComfyUI/models/ipadapter/` |
| `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | `ComfyUI/models/clip_vision/` |

InsightFace buffalo models are pulled by the IPAdapter InsightFace loader on first use (CPU provider is fine on Apple Silicon). Restart ComfyUI after installing the custom node. Readiness item `ipadapter_faceid` turns green when node + weights are present.

## AnimateDiff video (optional)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
```

Place a motion module, e.g. `mm_sdxl_v10_beta.safetensors`, under:

`ComfyUI/models/animatediff_models/`

(or the Evolved `models/` folder). Generate with type **Video** in the app. Outputs are `.mp4` when Video Helper Suite is available; otherwise the job falls back to stub/still. Readiness item `animatediff` tracks this.

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
