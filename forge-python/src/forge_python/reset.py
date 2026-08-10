"""Full local data reset helpers."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from forge_python.config import Settings


def _wipe_dir(path: Path) -> int:
    """Remove directory contents; recreate empty dir. Returns removed entry count."""
    removed = 0
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return 0
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)
        removed += 1
    path.mkdir(parents=True, exist_ok=True)
    return removed


def reset_app_data(settings: Settings, *, include_app_models: bool = False) -> dict[str, Any]:
    """Wipe SQLite + generated media/uploads/vault under the app data dir.

    Never touches ComfyUI install or IFORGE_EXTRA_MODEL_DIRS (e.g. /Volumes/external/hfModels).
    """
    report: dict[str, Any] = {
        "data_dir": str(settings.data_dir),
        "removed": {},
        "include_app_models": include_app_models,
    }

    db_path = settings.db_path
    if db_path.exists():
        db_path.unlink()
        report["removed"]["database"] = str(db_path)
    # sqlite sidecars
    for side in (f"{db_path}-wal", f"{db_path}-shm", f"{db_path}-journal"):
        p = Path(side)
        if p.exists():
            p.unlink()

    report["removed"]["media"] = _wipe_dir(settings.media_dir)
    report["removed"]["generations"] = _wipe_dir(settings.generations_dir)
    report["removed"]["thumbnails"] = _wipe_dir(settings.thumbnails_dir)
    report["removed"]["uploads"] = _wipe_dir(settings.uploads_dir)
    report["removed"]["vault"] = _wipe_dir(settings.vault_dir)
    report["removed"]["vault_cache"] = _wipe_dir(settings.media_dir / "vault_cache")

    # Pre-media layout leftover (data_dir/uploads)
    legacy = settings.legacy_uploads_dir
    if legacy.exists() and legacy.resolve() != settings.uploads_dir.resolve():
        report["removed"]["legacy_uploads"] = _wipe_dir(legacy)

    if include_app_models:
        report["removed"]["models"] = _wipe_dir(settings.models_dir)
    else:
        report["removed"]["models"] = "kept"

    settings.ensure_directories()
    return report
