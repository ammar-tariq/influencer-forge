"""In-process async generation queue (concurrency = 1)."""

from __future__ import annotations

import asyncio
import logging
from collections import deque

from typing import TYPE_CHECKING

from forge_python.comfyui_client import ComfyUIClient, _video_faceid_enabled
from forge_python.db import Database, body_from_json
from forge_python.llm_manager import (
    build_looks_prompt,
    expand_prompt,
    openai_enrich_scene,
    resolve_face_lock_path,
    resolve_negative_prompt,
    resolve_provider_settings,
)
from forge_python.prompt_layers import ClothingConflictError, resolve_prompt_layers

if TYPE_CHECKING:
    from forge_python.vault import VaultService

logger = logging.getLogger(__name__)


class QueueWorker:
    def __init__(self, db: Database, vault: VaultService | None = None) -> None:
        self.db = db
        self.vault = vault
        self.comfy = ComfyUIClient()
        self._queue: deque[int] = deque()
        self._task: asyncio.Task[None] | None = None
        self._paused = False
        self._wake = asyncio.Event()
        self._require_real: dict[int, bool] = {}
        self._current_id: int | None = None

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
        self._wake.set()

    def clear(self) -> int:
        """Drop pending jobs from the in-memory queue. Returns count removed."""
        count = len(self._queue)
        self._queue.clear()
        self._require_real.clear()
        return count

    async def stop(self) -> None:
        """Cancel the worker loop so shutdown/reset does not touch a closed DB."""
        self.pause()
        self.clear()
        self._wake.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    def status(self) -> dict[str, int | bool]:
        # Worker loop stays alive when idle — only count an active job.
        busy = bool(getattr(self, "_current_id", None))
        return {
            "pending": len(self._queue),
            "processing": 1 if busy and not self._paused else 0,
            "paused": self._paused,
        }

    async def start(self) -> None:
        # Re-queue unfinished jobs after restart
        rows = await self.db.fetchall(
            "SELECT id FROM generations WHERE status IN ('pending', 'queued', 'processing') ORDER BY id"
        )
        for row in rows:
            self._queue.append(int(row["id"]))
            await self.db.execute(
                "UPDATE generations SET status = 'queued' WHERE id = ?",
                (int(row["id"]),),
            )
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def enqueue(self, generation_id: int, *, require_real: bool = False) -> None:
        await self.db.execute(
            "UPDATE generations SET status = 'queued' WHERE id = ?",
            (generation_id,),
        )
        self._require_real[generation_id] = require_real
        self._queue.append(generation_id)
        self._wake.set()
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while True:
            if self._paused or not self._queue:
                self._wake.clear()
                await self._wake.wait()
                continue
            generation_id = self._queue.popleft()
            self._current_id = generation_id
            try:
                await self._process(generation_id)
            except Exception as exc:
                logger.exception("Generation %s failed", generation_id)
                await self.db.execute(
                    """
                    UPDATE generations
                    SET status = 'failed', error_message = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (str(exc), generation_id),
                )
            finally:
                self._require_real.pop(generation_id, None)
                self._current_id = None

    async def _process(self, generation_id: int) -> None:
        row = await self.db.fetchone("SELECT * FROM generations WHERE id = ?", (generation_id,))
        if not row:
            return
        await self.db.execute(
            "UPDATE generations SET status = 'processing' WHERE id = ?",
            (generation_id,),
        )
        influencer = await self.db.fetchone(
            "SELECT * FROM influencers WHERE id = ?",
            (row["influencer_id"],),
        )
        looks = None
        personality = None
        if influencer:
            looks = await self.db.fetchone("SELECT * FROM looks WHERE id = ?", (influencer["looks_id"],))
            personality = await self.db.fetchone(
                "SELECT * FROM personalities WHERE id = ?",
                (influencer["personality_id"],),
            )
        identity_explore = bool(row.get("identity_explore"))
        face_reference = None if identity_explore else resolve_face_lock_path(looks)
        # Only claim "same person as reference" when FaceID/img2img will actually run.
        workflow = str(row["workflow_type"] or "image")
        face_locked = bool(face_reference) and (
            workflow != "video" or _video_faceid_enabled()
        )
        wardrobe_keywords = None
        wardrobe_id = row.get("wardrobe_item_id")
        if wardrobe_id:
            item = await self.db.fetchone(
                "SELECT prompt_keywords FROM wardrobe_items WHERE id = ?",
                (wardrobe_id,),
            )
            if item:
                wardrobe_keywords = item["prompt_keywords"]
        try:
            layers = resolve_prompt_layers(
                str(row["user_prompt"]),
                wardrobe_keywords=wardrobe_keywords,
                is_nsfw_flag=bool(row.get("is_nsfw")),
            )
        except ClothingConflictError as exc:
            await self.db.execute(
                """
                UPDATE generations
                SET status = 'failed', error_message = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (str(exc), generation_id),
            )
            return
        is_nsfw = layers.is_nsfw
        body = body_from_json((looks or {}).get("body_json"))
        looks_prompt = build_looks_prompt(
            age=(looks or {}).get("age"),
            ethnicity=(looks or {}).get("ethnicity"),
            nationality=(looks or {}).get("nationality"),
            hair_color=(looks or {}).get("hair_color"),
            hair_style=(looks or {}).get("hair_style"),
            eye_color=(looks or {}).get("eye_color"),
            style=(looks or {}).get("style"),
            gender=(looks or {}).get("gender"),
            body=body,
            for_nsfw=is_nsfw,
            face_locked=face_locked,
        ) or (looks or {}).get("base_prompt") or "person"
        setting_rows = await self.db.fetchall("SELECT key, value FROM settings")
        settings_map = {str(r["key"]): str(r["value"] or "") for r in setting_rows}
        provider = resolve_provider_settings(settings_map)
        scene_text = layers.scene
        llm_used = "template"
        if provider == "openai":
            enriched = openai_enrich_scene(
                scene_text,
                api_key=settings_map.get("openai_api_key", ""),
                system_prompt=(personality or {}).get("system_prompt"),
            )
            if enriched:
                scene_text = enriched
                llm_used = "openai"
            else:
                logger.info("OpenAI enrich unavailable — using template scene")
        expanded = expand_prompt(
            scene_text,
            influencer_name=(influencer or {}).get("name") or "Influencer",
            looks_prompt=str(looks_prompt),
            wardrobe_keywords=layers.wardrobe_keywords,
            system_prompt=(personality or {}).get("system_prompt"),
            provider=provider if llm_used == "openai" else "template",
            is_nsfw=is_nsfw,
            face_locked=face_locked,
            clothing_from_wardrobe=layers.clothing_from_wardrobe,
        )
        negative = resolve_negative_prompt(
            is_nsfw=is_nsfw,
            user_prompt=layers.scene,
            wardrobe_keywords=layers.wardrobe_keywords,
            clothing_from_wardrobe=layers.clothing_from_wardrobe,
            age=(looks or {}).get("age"),
        )
        await self.db.execute(
            """
            UPDATE generations
            SET expanded_prompt = ?, negative_prompt = ?, is_nsfw = ?, llm_used = ?
            WHERE id = ?
            """,
            (expanded, negative, int(is_nsfw), llm_used, generation_id),
        )
        require_real = self._require_real.get(generation_id, False)
        out, thumb, seed, model = await self.comfy.generate(
            generation_id=generation_id,
            prompt=expanded,
            aspect_ratio=row["aspect_ratio"],
            seed=row["seed"],
            workflow_type=row["workflow_type"],
            face_reference=face_reference,
            allow_stub=not require_real,
            negative=negative,
            is_nsfw=is_nsfw,
        )
        await self.db.execute(
            """
            UPDATE generations
            SET status = 'completed',
                output_path = ?,
                output_thumbnail_path = ?,
                seed = ?,
                model_used = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (str(out), str(thumb), seed, model, generation_id),
        )
        # NSFW always goes into the vault automatically — no manual "Move to vault".
        # Requires a configured vault that is currently unlocked (PIN session).
        # If locked, the file stays pending and is vaulted on the next unlock.
        if is_nsfw and self.vault is not None:
            try:
                if await self.vault.is_configured() and self.vault.unlocked:
                    await self.vault.vault_generation(generation_id)
                    logger.info("Auto-vaulted NSFW generation %s", generation_id)
                elif await self.vault.is_configured():
                    logger.info(
                        "NSFW gen %s pending vault — will encrypt on next unlock",
                        generation_id,
                    )
            except (RuntimeError, ValueError, OSError) as exc:
                logger.warning("Auto-vault skipped for %s: %s", generation_id, exc)
