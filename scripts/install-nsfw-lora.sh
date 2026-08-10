#!/usr/bin/env bash
# Place an NSFW LoRA into ComfyUI/models/loras/ so NSFW generations can auto-inject it.
# Does not vendor adult weights into git. Provide a local file or URL yourself.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFY="${IFORGE_COMFYUI_ROOT:-$ROOT/src-tauri/resources/comfyui/ComfyUI}"
LORAS="$COMFY/models/loras"
mkdir -p "$LORAS"

SRC="${1:-${IFORGE_NSFW_LORA_PATH:-}}"
URL="${IFORGE_NSFW_LORA_URL:-}"

if [[ -z "$SRC" && -z "$URL" ]]; then
  cat >&2 <<'EOF'
Usage:
  ./scripts/install-nsfw-lora.sh /path/to/your_nsfw_lora.safetensors
  # or:
  IFORGE_NSFW_LORA_URL='https://…/something_nsfw.safetensors' ./scripts/install-nsfw-lora.sh

The filename must contain nsfw, nude, or explicit (case-insensitive) so the
orchestrator picks it up for NSFW jobs.
EOF
  exit 1
fi

if [[ -n "$SRC" ]]; then
  SRC="$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")"
  if [[ ! -f "$SRC" ]]; then
    echo "File not found: $SRC" >&2
    exit 1
  fi
  base="$(basename "$SRC")"
  lower="$(echo "$base" | tr '[:upper:]' '[:lower:]')"
  if [[ "$lower" != *nsfw* && "$lower" != *nude* && "$lower" != *explicit* ]]; then
    dest="$LORAS/nsfw_${base}"
  else
    dest="$LORAS/$base"
  fi
  cp -f "$SRC" "$dest"
  echo "Installed NSFW LoRA → $dest"
  exit 0
fi

name="$(basename "${URL%%\?*}")"
lower="$(echo "$name" | tr '[:upper:]' '[:lower:]')"
if [[ "$lower" != *nsfw* && "$lower" != *nude* && "$lower" != *explicit* ]]; then
  name="nsfw_${name}"
fi
dest="$LORAS/$name"
echo "Downloading → $dest"
curl -L --fail --retry 3 -C - "$URL" -o "$dest"
echo "Installed NSFW LoRA → $dest"
echo "Restart is not required for the orchestrator; next NSFW job will inject LoraLoader."
