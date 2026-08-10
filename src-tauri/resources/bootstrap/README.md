# Bootstrap resources

In development, the Tauri shell starts the orchestrator from the repo `forge-python/` package using system Python / the local `.venv`.

For release packaging (Phase 3), place a portable Python runtime under `resources/python/` and keep thin launch helpers here.
