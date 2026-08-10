"""Content schedule reminders via APScheduler."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from forge_python.db import Database

logger = logging.getLogger(__name__)


class ScheduleService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.scheduler = AsyncIOScheduler()
        self.due_reminders: list[dict[str, Any]] = []

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            self.scheduler.add_job(self.tick, "interval", seconds=30, id="schedule-tick")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def tick(self) -> None:
        rows = await self.db.fetchall("SELECT * FROM schedules WHERE is_active = 1")
        now = datetime.now()
        for row in rows:
            next_trigger = row.get("next_trigger")
            if not next_trigger:
                next_dt = self._compute_next(row["schedule_time"], row["frequency"], now)
                await self.db.execute(
                    "UPDATE schedules SET next_trigger = ? WHERE id = ?",
                    (next_dt.isoformat(sep=" ", timespec="seconds"), row["id"]),
                )
                continue
            try:
                due_at = datetime.fromisoformat(str(next_trigger))
            except ValueError:
                continue
            if due_at <= now:
                self.due_reminders.append(
                    {
                        "schedule_id": row["id"],
                        "influencer_id": row["influencer_id"],
                        "prompt_template": row["prompt_template"],
                        "triggered_at": now.isoformat(sep=" ", timespec="seconds"),
                    }
                )
                nxt = self._compute_next(row["schedule_time"], row["frequency"], now + timedelta(minutes=1))
                await self.db.execute(
                    """
                    UPDATE schedules
                    SET last_triggered = ?, next_trigger = ?
                    WHERE id = ?
                    """,
                    (
                        now.isoformat(sep=" ", timespec="seconds"),
                        nxt.isoformat(sep=" ", timespec="seconds"),
                        row["id"],
                    ),
                )
                logger.info("Schedule %s triggered", row["id"])

    def pop_reminders(self) -> list[dict[str, Any]]:
        items = list(self.due_reminders)
        self.due_reminders.clear()
        return items

    @staticmethod
    def _compute_next(schedule_time: str, frequency: str, after: datetime) -> datetime:
        hour, minute, *_ = [int(x) for x in (schedule_time.split(":") + ["0", "0"])[:3]]
        candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= after:
            if frequency == "weekly":
                candidate += timedelta(days=7)
            elif frequency == "monthly":
                candidate += timedelta(days=30)
            else:
                candidate += timedelta(days=1)
        return candidate

    @staticmethod
    def dumps_scenes(scenes: list[str] | None) -> str | None:
        return json.dumps(scenes) if scenes is not None else None
