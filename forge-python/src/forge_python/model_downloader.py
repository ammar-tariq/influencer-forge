"""Model download scaffolding (disabled in Phase 1 by default)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from forge_python.config import settings


@dataclass
class DownloadProgress:
    ready: bool = False
    progress: float = 0.0
    stage: str = "init"
    message: str = "Starting bootstrap"
    steps: list[dict[str, Any]] = field(default_factory=list)


class ModelDownloader:
    """Phase 1: local readiness only. Phase 2+: HuggingFace downloads when enabled."""

    def __init__(self) -> None:
        self.state = DownloadProgress()

    async def run_bootstrap(self) -> DownloadProgress:
        steps = [
            {"id": "dirs", "label": "Create app directories", "status": "pending"},
            {"id": "db", "label": "Initialize database", "status": "pending"},
            {"id": "deps", "label": "Verify Python runtime", "status": "pending"},
            {"id": "models", "label": "Model assets", "status": "pending"},
        ]
        self.state.steps = steps
        self.state.stage = "dirs"
        self.state.message = "Creating application directories"
        self.state.progress = 10
        settings.ensure_directories()
        steps[0]["status"] = "done"

        self.state.stage = "db"
        self.state.message = "Database path ready"
        self.state.progress = 40
        steps[1]["status"] = "done"

        self.state.stage = "deps"
        self.state.message = "Python runtime OK"
        self.state.progress = 70
        steps[2]["status"] = "done"

        self.state.stage = "models"
        if settings.enable_model_downloads:
            self.state.message = "Model downloads enabled (HuggingFace) — not bundling weights in git"
            # Placeholder for resumable HF downloads in Phase 2.
            steps[3]["status"] = "skipped"
            steps[3]["detail"] = "Configure IFORGE_ENABLE_MODEL_DOWNLOADS and HF cache under models/"
        else:
            self.state.message = "Skipping model downloads (stub generation mode)"
            steps[3]["status"] = "skipped"
        self.state.progress = 100
        self.state.ready = True
        self.state.stage = "ready"
        return self.state
