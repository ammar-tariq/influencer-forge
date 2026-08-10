"""SQLite schema and data access."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

from forge_python.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS personalities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    bio TEXT,
    traits TEXT NOT NULL,
    niche TEXT NOT NULL,
    age_rating TEXT NOT NULL,
    system_prompt TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS looks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    ethnicity TEXT,
    hair_color TEXT,
    hair_style TEXT,
    eye_color TEXT,
    style TEXT,
    body_json TEXT,
    base_prompt TEXT,
    reference_image_path TEXT,
    face_embedding BLOB,
    lora_path TEXT,
    base_portrait_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS influencers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personality_id INTEGER NOT NULL,
    looks_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (personality_id) REFERENCES personalities(id),
    FOREIGN KEY (looks_id) REFERENCES looks(id)
);

CREATE TABLE IF NOT EXISTS wardrobe_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    prompt_keywords TEXT NOT NULL,
    preview_image TEXT,
    is_shared BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS influencer_wardrobe (
    influencer_id INTEGER NOT NULL,
    wardrobe_item_id INTEGER NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (influencer_id, wardrobe_item_id),
    FOREIGN KEY (influencer_id) REFERENCES influencers(id),
    FOREIGN KEY (wardrobe_item_id) REFERENCES wardrobe_items(id)
);

CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    influencer_id INTEGER NOT NULL,
    parent_generation_id INTEGER,
    user_prompt TEXT NOT NULL,
    expanded_prompt TEXT NOT NULL,
    negative_prompt TEXT,
    workflow_type TEXT NOT NULL,
    model_used TEXT NOT NULL,
    llm_used TEXT NOT NULL,
    aspect_ratio TEXT NOT NULL,
    seed INTEGER,
    steps INTEGER,
    cfg_scale REAL,
    output_path TEXT,
    output_thumbnail_path TEXT,
    is_nsfw BOOLEAN DEFAULT 0,
    is_vaulted BOOLEAN DEFAULT 0,
    vault_file_path TEXT,
    teaser_path TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (influencer_id) REFERENCES influencers(id),
    FOREIGN KEY (parent_generation_id) REFERENCES generations(id)
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    influencer_id INTEGER NOT NULL,
    schedule_time TEXT NOT NULL,
    frequency TEXT NOT NULL,
    cron_expression TEXT,
    prompt_template TEXT NOT NULL,
    scene_suggestions TEXT,
    wardrobe_item_id INTEGER,
    is_active BOOLEAN DEFAULT 1,
    calendar_event_id TEXT,
    calendar_provider TEXT,
    last_triggered DATETIME,
    next_trigger DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (influencer_id) REFERENCES influencers(id),
    FOREIGN KEY (wardrobe_item_id) REFERENCES wardrobe_items(id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vault_metadata (
    id INTEGER PRIMARY KEY,
    pin_hash TEXT NOT NULL,
    pin_salt TEXT NOT NULL,
    vault_path TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        settings.ensure_directories()
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._migrate_looks_columns()
        await self._conn.commit()

    async def _migrate_looks_columns(self) -> None:
        """Add gender/body_json on existing DBs created before those columns existed."""
        cur = await self.conn.execute("PRAGMA table_info(looks)")
        cols = {row[1] for row in await cur.fetchall()}
        if "gender" not in cols:
            await self.conn.execute("ALTER TABLE looks ADD COLUMN gender TEXT")
        if "body_json" not in cols:
            await self.conn.execute("ALTER TABLE looks ADD COLUMN body_json TEXT")

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        cur = await self.conn.execute(sql, params)
        row = await cur.fetchone()
        return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cur = await self.conn.execute(sql, params)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = await self.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        await self.execute(
            """
            INSERT INTO settings(key, value, updated_at) VALUES(?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )


def traits_to_json(traits: dict[str, str]) -> str:
    return json.dumps(traits)


def traits_from_json(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    data = json.loads(raw)
    return {str(k): str(v) for k, v in data.items()}


def body_to_json(body: dict[str, str] | None) -> str | None:
    if not body:
        return None
    cleaned = {str(k): str(v) for k, v in body.items() if v}
    return json.dumps(cleaned) if cleaned else None


def body_from_json(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in data.items() if v}
