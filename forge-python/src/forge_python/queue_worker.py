"""In-process async generation queue (concurrency = 1)."""

from __future__ import annotations

import asyncio
import logging
from collections import deque

from forge_python.comfyui_client import ComfyUIClient
from forge_python.db import Database
from forge_python.llm_manager import expand_prompt

logger = logging.getLogger(__name__)


class QueueWorker:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.comfy = ComfyUIClient()
        self._queue: deque[int] = deque()
        self._task: asyncio.Task[None] | None = None
        self._paused = False
        self._wake = asyncio.Event()

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
        self._wake.set()

    def status(self) -> dict[str, int | bool]:
        return {
            "pending": len(self._queue),
            "processing": 1 if self._task and not self._task.done() and not self._paused else 0,
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

    async def enqueue(self, generation_id: int) -> None:
        await self.db.execute(
            "UPDATE generations SET status = 'queued' WHERE id = ?",
            (generation_id,),
        )
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
            try:
                await self._process(generation_id)
            except Exception as exc:  # noqa: BLE001 - surface to DB
                logger.exception("Generation %s failed", generation_id)
                await self.db.execute(
                    """
                    UPDATE generations
                    SET status = 'failed', error_message = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (str(exc), generation_id),
                )

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
        looks_prompt = (looks or {}).get("base_prompt") or "portrait"
        expanded = expand_prompt(
            row["user_prompt"],
            influencer_name=(influencer or {}).get("name") or "Influencer",
            looks_prompt=str(looks_prompt),
            system_prompt=(personality or {}).get("system_prompt"),
        )
        await self.db.execute(
            "UPDATE generations SET expanded_prompt = ? WHERE id = ?",
            (expanded, generation_id),
        )
        out, thumb, seed, model = await self.comfy.generate(
            generation_id=generation_id,
            prompt=expanded,
            aspect_ratio=row["aspect_ratio"],
            seed=row["seed"],
            workflow_type=row["workflow_type"],
            face_reference=(looks or {}).get("reference_image_path"),
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
