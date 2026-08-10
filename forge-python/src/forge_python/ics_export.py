"""Build iCalendar (.ics) feeds from InfluencerForge schedules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _fold(line: str) -> str:
    """RFC 5545 line folding at 75 octets (approx chars for ASCII)."""
    if len(line) <= 75:
        return line
    chunks = [line[:75]]
    rest = line[75:]
    while rest:
        chunks.append(" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(chunks)


def _fmt_local(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_schedule_time(schedule_time: str, after: datetime) -> datetime:
    parts = (schedule_time or "09:00:00").split(":")
    hour = int(parts[0]) if parts else 9
    minute = int(parts[1]) if len(parts) > 1 else 0
    second = int(parts[2]) if len(parts) > 2 else 0
    return after.replace(hour=hour, minute=minute, second=second, microsecond=0)


def _rrule(frequency: str) -> str | None:
    freq = (frequency or "daily").lower()
    if freq == "weekly":
        return "FREQ=WEEKLY"
    if freq == "monthly":
        return "FREQ=MONTHLY"
    if freq == "custom":
        return "FREQ=DAILY"  # custom cron not exported; daily recurrence as fallback
    return "FREQ=DAILY"


def build_vevent(
    row: Mapping[str, Any],
    *,
    influencer_name: str,
    now: datetime | None = None,
) -> list[str]:
    now = now or datetime.now(timezone.utc).astimezone()
    sid = int(row["id"])
    dtstart = _parse_schedule_time(str(row.get("schedule_time") or "09:00:00"), now)
    if dtstart <= now:
        # Prefer next_trigger when present and parseable.
        nxt = row.get("next_trigger")
        if nxt:
            try:
                dtstart = datetime.fromisoformat(str(nxt))
            except ValueError:
                pass
    summary = f"InfluencerForge: {influencer_name}"
    desc = str(row.get("prompt_template") or "Create a post")
    lines = [
        "BEGIN:VEVENT",
        f"UID:iforge-schedule-{sid}@localhost",
        f"DTSTAMP:{_fmt_utc(now)}",
        f"DTSTART:{_fmt_local(dtstart)}",
    ]
    rrule = _rrule(str(row.get("frequency") or "daily"))
    if rrule:
        lines.append(f"RRULE:{rrule}")
    lines.append(f"SUMMARY:{_escape(summary)}")
    lines.append(f"DESCRIPTION:{_escape(desc)}")
    lines.append("END:VEVENT")
    return lines


def build_calendar(
    rows: list[Mapping[str, Any]],
    *,
    names: Mapping[int, str] | None = None,
    now: datetime | None = None,
) -> str:
    """Return a VCALENDAR string (CRLF). Skips inactive rows when is_active is present."""
    now = now or datetime.now(timezone.utc).astimezone()
    names = names or {}
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//InfluencerForge//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:InfluencerForge Schedules",
    ]
    for row in rows:
        if "is_active" in row and not bool(row["is_active"]):
            continue
        iid = int(row["influencer_id"])
        name = names.get(iid) or f"Influencer #{iid}"
        lines.extend(build_vevent(row, influencer_name=name, now=now))
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
