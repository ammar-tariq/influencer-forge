#!/usr/bin/env bash
# Install ComfyUI_InstantID custom node + InstantX weights + antelopev2.
# App generation still prefers IP-Adapter FaceID; InstantID is an optional alternate.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFY="${IFORGE_COMFYUI_ROOT:-$ROOT/src-tauri/resources/comfyui/ComfyUI}"
NODE="$COMFY/custom_nodes/ComfyUI_InstantID"

if [[ ! -d "$COMFY" ]]; then
  echo "ComfyUI not found at $COMFY — clone it first (see src-tauri/resources/comfyui/README.md)" >&2
  exit 1
fi

if [[ ! -d "$NODE/.git" ]]; then
  git clone --depth 1 https://github.com/cubiq/ComfyUI_InstantID.git "$NODE"
fi

PY="${COMFY}/.venv/bin/python"
if [[ -x "$PY" ]]; then
  uv pip install --python "$PY" insightface onnxruntime opencv-python-headless 2>/dev/null \
    || "$PY" -m pip install insightface onnxruntime opencv-python-headless || true
  if [[ -f "$NODE/requirements.txt" ]]; then
    uv pip install --python "$PY" -r "$NODE/requirements.txt" 2>/dev/null \
      || "$PY" -m pip install -r "$NODE/requirements.txt" || true
  fi
fi

mkdir -p "$COMFY/models/instantid" "$COMFY/models/controlnet" \
  "$COMFY/models/insightface/models/antelopev2"

IPA="$COMFY/models/instantid/ip-adapter.bin"
CN="$COMFY/models/controlnet/instantid_sdxl_controlnet.safetensors"
if [[ ! -f "$IPA" ]]; then
  echo "Downloading InstantID ip-adapter.bin…"
  curl -L --fail --retry 3 -C - \
    "https://huggingface.co/InstantX/InstantID/resolve/main/ip-adapter.bin" -o "$IPA"
fi
if [[ ! -f "$CN" ]]; then
  echo "Downloading InstantID ControlNet…"
  curl -L --fail --retry 3 -C - \
    "https://huggingface.co/InstantX/InstantID/resolve/main/ControlNetModel/diffusion_pytorch_model.safetensors" \
    -o "$CN"
fi

ANT="$COMFY/models/insightface/models/antelopev2"
if [[ ! -f "$ANT/scrfd_10g_bnkps.onnx" ]]; then
  echo "Downloading InsightFace antelopev2…"
  for f in 1k3d68.onnx 2d106det.onnx genderage.onnx glintr100.onnx scrfd_10g_bnkps.onnx; do
    curl -L --fail --retry 3 -C - \
      "https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/$f" -o "$ANT/$f" \
      || curl -L --fail --retry 3 -C - \
      "https://huggingface.co/MonsterMMORPG/tools/resolve/main/$f" -o "$ANT/$f"
  done
fi

echo "InstantID ready under $NODE"
echo "Restart ComfyUI. App generation still uses IP-Adapter FaceID / img2img as the primary path."
