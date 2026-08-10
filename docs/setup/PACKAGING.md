# Packaging & embedded Python

## Development (current)

Tauri resolves Python in this order:

1. `resources/python/python` (or `python.exe`) next to the binary / resources
2. `forge-python/.venv` when running from the repo
3. `python3` / `python` on `PATH`

## Release packaging (Phase 3 path)

1. Build a portable CPython (or copy a relocatable build) into `src-tauri/resources/python/`
2. Install orchestrator deps into that runtime’s `site-packages`
3. Keep models **out of git** — download into the user data dir on first launch when `IFORGE_ENABLE_MODEL_DOWNLOADS=1`
4. Produce installers via `.github/workflows/build.yml` (`dmg` / `AppImage` / `nsis`)

See `src-tauri/resources/bootstrap/README.md`.
