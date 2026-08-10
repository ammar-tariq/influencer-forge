"""Application paths and runtime configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "InfluencerForge"
API_HOST = "127.0.0.1"
API_PORT = 8765
COMFYUI_PORT = 8188


def default_data_dir() -> Path:
    """Resolve OS-specific application data directory."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(base) / APP_NAME
    return Path.home() / ".config" / APP_NAME


class Settings:
    """Runtime settings derived from environment variables."""

    def __init__(self) -> None:
        self.data_dir = Path(os.environ.get("IFORGE_DATA_DIR", str(default_data_dir())))
        self.host = os.environ.get("IFORGE_HOST", API_HOST)
        self.port = int(os.environ.get("IFORGE_PORT", str(API_PORT)))
        self.comfyui_port = int(os.environ.get("IFORGE_COMFYUI_PORT", str(COMFYUI_PORT)))
        self.comfyui_url = os.environ.get(
            "IFORGE_COMFYUI_URL", f"http://127.0.0.1:{self.comfyui_port}"
        )
        self.enable_comfyui = os.environ.get("IFORGE_ENABLE_COMFYUI", "0") == "1"
        self.enable_model_downloads = os.environ.get("IFORGE_ENABLE_MODEL_DOWNLOADS", "0") == "1"
        # When false, generation fails loudly instead of writing Pillow placeholders.
        self.allow_stub_fallback = os.environ.get("IFORGE_ALLOW_STUB_FALLBACK", "1") == "1"
        self.db_path = self.data_dir / "data.db"
        self.media_dir = self.data_dir / "media"
        self.generations_dir = self.media_dir / "generations"
        self.thumbnails_dir = self.media_dir / "thumbnails"
        self.models_dir = self.data_dir / "models"
        self.vault_dir = self.data_dir / "vault"
        self.uploads_dir = self.data_dir / "uploads"
        self.comfyui_root = Path(
            os.environ.get(
                "IFORGE_COMFYUI_ROOT",
                str(Path(__file__).resolve().parents[3] / "src-tauri" / "resources" / "comfyui" / "ComfyUI"),
            )
        )
        self.model_manifest_path = Path(
            os.environ.get(
                "IFORGE_MODEL_MANIFEST",
                str(Path(__file__).resolve().parents[3] / "src-tauri" / "resources" / "bootstrap" / "models.json"),
            )
        )
        self.workflows_dir = Path(
            os.environ.get(
                "IFORGE_WORKFLOWS_DIR",
                str(Path(__file__).resolve().parents[3] / "src-tauri" / "resources" / "workflows"),
            )
        )
        # Colon-separated extra dirs to scan for single-file checkpoints (e.g. /Volumes/external/hfModels)
        extra = os.environ.get("IFORGE_EXTRA_MODEL_DIRS", "/Volumes/external/hfModels")
        self.extra_model_dirs = [Path(p) for p in extra.split(":") if p.strip()]

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.media_dir,
            self.generations_dir,
            self.thumbnails_dir,
            self.models_dir,
            self.vault_dir,
            self.uploads_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
