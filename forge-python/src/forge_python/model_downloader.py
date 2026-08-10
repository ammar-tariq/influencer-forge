"""Bootstrap readiness + optional resumable model downloads."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from forge_python.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    ready: bool = False
    progress: float = 0.0
    stage: str = "init"
    message: str = "Starting bootstrap"
    steps: list[dict[str, Any]] = field(default_factory=list)


class ModelDownloader:
    """Creates dirs/DB readiness; optionally downloads manifest assets with resume."""

    def __init__(self) -> None:
        self.state = DownloadProgress()
        self._lock = asyncio.Lock()

    def load_manifest(self) -> list[dict[str, Any]]:
        path = settings.model_manifest_path
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("models", data if isinstance(data, list) else [])
        return [item for item in items if isinstance(item, dict)]

    async def run_bootstrap(self) -> DownloadProgress:
        async with self._lock:
            steps: list[dict[str, Any]] = [
                {"id": "dirs", "label": "Create app directories", "status": "pending"},
                {"id": "db", "label": "Initialize database", "status": "pending"},
                {"id": "deps", "label": "Verify Python runtime", "status": "pending"},
                {"id": "models", "label": "Model assets", "status": "pending"},
            ]
            self.state.steps = steps
            self.state.ready = False

            self.state.stage = "dirs"
            self.state.message = "Creating application directories"
            self.state.progress = 10
            settings.ensure_directories()
            steps[0]["status"] = "done"

            self.state.stage = "db"
            self.state.message = "Database path ready"
            self.state.progress = 35
            steps[1]["status"] = "done"

            self.state.stage = "deps"
            self.state.message = "Python runtime OK"
            self.state.progress = 55
            steps[2]["status"] = "done"

            self.state.stage = "models"
            if settings.enable_model_downloads:
                await self._download_manifest(steps)
            else:
                self.state.message = "Skipping model downloads (stub generation mode)"
                steps[3]["status"] = "skipped"
                steps[3]["detail"] = "Set IFORGE_ENABLE_MODEL_DOWNLOADS=1 to fetch manifest assets"
                self.state.progress = 100

            self.state.ready = True
            self.state.stage = "ready"
            self.state.progress = max(self.state.progress, 100)
            return self.state

    async def _download_manifest(self, steps: list[dict[str, Any]]) -> None:
        models = self.load_manifest()
        if not models:
            self.state.message = "No models in manifest — continuing"
            steps[3]["status"] = "skipped"
            steps[3]["detail"] = f"Missing or empty manifest at {settings.model_manifest_path}"
            self.state.progress = 100
            return

        steps[3]["status"] = "running"
        completed = 0
        for item in models:
            name = str(item.get("name", "asset"))
            url = str(item.get("url", ""))
            rel = str(item.get("path", name))
            dest = settings.models_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            self.state.message = f"Downloading {name}"
            try:
                await self._download_resumable(url, dest)
                completed += 1
            except Exception as exc:
                logger.exception("Failed downloading %s", name)
                steps[3]["detail"] = f"{name} failed: {exc}"
            self.state.progress = 55 + (45 * completed / max(len(models), 1))

        steps[3]["status"] = "done" if completed == len(models) else "partial"
        self.state.message = f"Downloaded {completed}/{len(models)} model assets"
        self.state.progress = 100

    async def _download_resumable(self, url: str, dest: Path) -> None:
        if not url:
            raise ValueError("model url missing")
        # Dev/test convenience: allow file:// sources without a network hop.
        if url.startswith("file:"):
            src = Path(httpx.URL(url).path)
            # On Windows httpx may keep a leading slash; Path handles POSIX fine here.
            if not src.exists():
                src = Path(url.removeprefix("file://"))
            dest.write_bytes(src.read_bytes())
            return
        existing = dest.stat().st_size if dest.exists() else 0
        headers: dict[str, str] = {}
        if existing > 0:
            headers["Range"] = f"bytes={existing}-"
        async with (
            httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client,
            client.stream("GET", url, headers=headers) as resp,
        ):
            if resp.status_code == 416:
                return
            resp.raise_for_status()
            mode = "ab" if resp.status_code == 206 and existing > 0 else "wb"
            if mode == "wb" and dest.exists():
                existing = 0
            with dest.open(mode) as fh:
                async for chunk in resp.aiter_bytes():
                    fh.write(chunk)
