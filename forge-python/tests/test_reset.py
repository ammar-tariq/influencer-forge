from pathlib import Path

from PIL import Image

from forge_python.config import Settings
from forge_python.reset import reset_app_data


def test_reset_wipes_db_and_media(tmp_path: Path) -> None:
    s = Settings()
    s.data_dir = tmp_path
    s.db_path = tmp_path / "data.db"
    s.media_dir = tmp_path / "media"
    s.generations_dir = s.media_dir / "generations"
    s.thumbnails_dir = s.media_dir / "thumbnails"
    s.models_dir = tmp_path / "models"
    s.vault_dir = tmp_path / "vault"
    s.uploads_dir = tmp_path / "uploads"
    s.ensure_directories()

    s.db_path.write_text("sqlite-junk", encoding="utf-8")
    Image.new("RGB", (8, 8), (1, 2, 3)).save(s.generations_dir / "1.png")
    (s.uploads_dir / "face.png").write_bytes(b"x")
    (s.vault_dir / "secret.bin").write_bytes(b"enc")
    keep = s.models_dir / "keep.bin"
    keep.write_bytes(b"model")

    report = reset_app_data(s, include_app_models=False)
    assert not s.db_path.exists()
    assert list(s.generations_dir.iterdir()) == []
    assert list(s.uploads_dir.iterdir()) == []
    assert list(s.vault_dir.iterdir()) == []
    assert keep.exists()
    assert report["removed"]["models"] == "kept"

    reset_app_data(s, include_app_models=True)
    assert list(s.models_dir.iterdir()) == []
