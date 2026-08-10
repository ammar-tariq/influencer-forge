#!/usr/bin/env bash
# Install ComfyUI_wav2lip custom node + wav2lip_gan.pth checkpoint.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFY="${IFORGE_COMFYUI_ROOT:-$ROOT/src-tauri/resources/comfyui/ComfyUI}"
NODE="$COMFY/custom_nodes/ComfyUI_wav2lip"
CKPT="$NODE/checkpoints/wav2lip_gan.pth"
URL="${WAV2LIP_MODEL_URL:-https://huggingface.co/Nekochu/Wav2Lip/resolve/main/wav2lip_gan.pth}"

if [[ ! -d "$COMFY" ]]; then
  echo "ComfyUI not found at $COMFY — clone it first (see src-tauri/resources/comfyui/README.md)" >&2
  exit 1
fi

if [[ ! -d "$NODE/.git" ]]; then
  git clone --depth 1 https://github.com/ShmuelRonen/ComfyUI_wav2lip.git "$NODE"
fi

mkdir -p "$NODE/checkpoints"
if [[ ! -f "$CKPT" ]]; then
  echo "Downloading wav2lip_gan.pth (~416 MB)…"
  curl -L --fail --retry 3 -C - "$URL" -o "$CKPT"
fi

PY="${COMFY}/.venv/bin/python"
if [[ -x "$PY" ]]; then
  uv pip install --python "$PY" -r "$NODE/requirements.txt" 2>/dev/null \
    || "$PY" -m pip install -r "$NODE/requirements.txt" || true
fi

echo "Wav2Lip ready: $CKPT"
echo "Restart ComfyUI, then Create post → Talking head will prefer Wav2Lip when the node is live."
