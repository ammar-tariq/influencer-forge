#!/usr/bin/env bash
# Assemble a relocatable CPython + forge-python package into
# src-tauri/resources/{python,forge-python} for release bundles.
# Multi-GB diffusion weights are NOT included — download at runtime.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_PYTHON="${IFORGE_PORTABLE_PYTHON_DIR:-$ROOT/src-tauri/resources/python}"
OUT_FORGE="${IFORGE_PORTABLE_FORGE_DIR:-$ROOT/src-tauri/resources/forge-python}"
PY_VERSION="${IFORGE_PORTABLE_PYTHON_VERSION:-3.12}"

echo "==> Assembling portable Python → $OUT_PYTHON"
echo "==> Copying forge-python src → $OUT_FORGE"

command -v uv >/dev/null 2>&1 || {
  echo "uv is required (https://docs.astral.sh/uv/)" >&2
  exit 1
}

rm -rf "$OUT_PYTHON" "$OUT_FORGE"
mkdir -p "$OUT_PYTHON" "$OUT_FORGE"

# Standalone CPython managed by uv (relocatable enough for Tauri resources).
uv python install "$PY_VERSION"
UV_PYTHON="$(uv python find "$PY_VERSION")"
PYTHON_HOME="$(cd "$(dirname "$UV_PYTHON")/.." && pwd)"

echo "Using uv Python at $PYTHON_HOME"
# Copy the interpreter tree (bin/lib/include) into resources/python
copy_tree() {
  local src="$1" dest="$2"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --exclude '__pycache__' --exclude '*.pyc' "$src/" "$dest/"
  else
    mkdir -p "$dest"
    cp -R "$src/." "$dest/"
  fi
}
copy_tree "$PYTHON_HOME" "$OUT_PYTHON"

PORTABLE_PY="$OUT_PYTHON/bin/python3"
if [[ ! -x "$PORTABLE_PY" ]]; then
  PORTABLE_PY="$OUT_PYTHON/bin/python"
fi
if [[ ! -x "$PORTABLE_PY" ]]; then
  PORTABLE_PY="$OUT_PYTHON/python.exe"
fi
if [[ ! -e "$PORTABLE_PY" ]]; then
  echo "Portable interpreter not found under $OUT_PYTHON" >&2
  exit 1
fi

# Symlink bare `python` for resolve_python() on Unix
if [[ -x "$OUT_PYTHON/bin/python3" && ! -e "$OUT_PYTHON/bin/python" ]]; then
  ln -sf python3 "$OUT_PYTHON/bin/python"
fi
# Also expose top-level python for Tauri resolve_python layout
if [[ -x "$OUT_PYTHON/bin/python" && ! -e "$OUT_PYTHON/python" ]]; then
  ln -sf "bin/python" "$OUT_PYTHON/python"
fi

echo "==> Installing forge-python runtime deps into portable site-packages"
"$PORTABLE_PY" -m ensurepip --upgrade 2>/dev/null || true
"$PORTABLE_PY" -m pip install --upgrade pip
"$PORTABLE_PY" -m pip install \
  "aiosqlite>=0.22.1" \
  "apscheduler>=3.11.3" \
  "argon2-cffi>=25.1.0" \
  "cryptography>=50.0.0" \
  "fastapi>=0.141.1" \
  "httpx>=0.28.1" \
  "pillow>=12.3.0" \
  "psutil>=7.2.2" \
  "pydantic>=2.13.4" \
  "python-multipart>=0.0.32" \
  "uvicorn[standard]>=0.52.1"

echo "==> Freezing forge-python sources (no .venv / tests)"
mkdir -p "$OUT_FORGE/src"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    "$ROOT/forge-python/src/" "$OUT_FORGE/src/"
else
  cp -R "$ROOT/forge-python/src/." "$OUT_FORGE/src/"
fi
cp "$ROOT/forge-python/pyproject.toml" "$OUT_FORGE/pyproject.toml"
cat > "$OUT_FORGE/README.md" <<'EOF'
# Bundled forge-python

Frozen copy of the orchestrator package for release builds.
Created by `scripts/assemble-portable-python.sh`. Do not edit by hand.
EOF

cat > "$OUT_PYTHON/README.md" <<'EOF'
# Bundled portable Python

Created by `scripts/assemble-portable-python.sh`. Not committed to git (see `.gitignore`).
Weights / ComfyUI stay outside this tree — see `docs/setup/PACKAGING.md`.
EOF

echo "==> Done"
echo "    Python: $("$PORTABLE_PY" -c 'import sys; print(sys.version)')"
echo "    Forge:  $OUT_FORGE/src/forge_python"
