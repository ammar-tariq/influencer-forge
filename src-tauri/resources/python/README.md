# Embedded Python (release packaging)

Place a portable CPython runtime here for Phase 3 release builds:

- `python` / `python.exe`
- `Lib/site-packages` (or equivalent) with orchestrator dependencies

Development ignores this folder and uses `forge-python/.venv` or system Python.
See `docs/setup/PACKAGING.md`.
