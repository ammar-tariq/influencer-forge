"""Google Calendar sync for schedules (optional OAuth refresh token).

Apple Calendar: use ICS export (no OAuth). Google: Settings store
google_client_id / google_client_secret / google_refresh_token, then
POST /api/schedules/sync-google creates/updates events.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
CAL_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPES = "https://www.googleapis.com/auth/calendar.events"


def google_auth_url(client_id: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
    q = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return f"{AUTH_URL}?{q}"


def exchange_code_for_tokens(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob",
) -> dict[str, str]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code.strip(),
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    refresh = str(data.get("refresh_token") or "")
    access = str(data.get("access_token") or "")
    if not access:
        raise RuntimeError("Google token exchange failed — no access_token")
    return {"access_token": access, "refresh_token": refresh}


def refresh_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> str:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        data = resp.json()
    token = str(data.get("access_token") or "")
    if not token:
        raise RuntimeError("Google refresh failed — no access_token")
    return token


def _parse_time(schedule_time: str, day: datetime) -> datetime:
    parts = (schedule_time or "09:00:00").split(":")
    hour = int(parts[0]) if parts else 9
    minute = int(parts[1]) if len(parts) > 1 else 0
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _rrule(frequency: str) -> str | None:
    freq = (frequency or "daily").lower()
    if freq == "weekly":
        return "RRULE:FREQ=WEEKLY"
    if freq == "monthly":
        return "RRULE:FREQ=MONTHLY"
    if freq == "custom":
        return "RRULE:FREQ=DAILY"
    return "RRULE:FREQ=DAILY"


def upsert_schedule_event(
    *,
    access_token: str,
    schedule: dict[str, Any],
    influencer_name: str,
) -> str:
    """Create or patch a Google Calendar event. Returns event id."""
    now = datetime.now(timezone.utc).astimezone()
    start = _parse_time(str(schedule.get("schedule_time") or "09:00:00"), now)
    if start <= now:
        start = start + timedelta(days=1)
    end = start + timedelta(minutes=30)
    summary = f"InfluencerForge: {influencer_name}"
    desc = str(schedule.get("prompt_template") or "Create a post")
    body: dict[str, Any] = {
        "summary": summary,
        "description": desc,
        "start": {"dateTime": start.isoformat(), "timeZone": str(start.tzinfo or "UTC")},
        "end": {"dateTime": end.isoformat(), "timeZone": str(end.tzinfo or "UTC")},
    }
    rrule = _rrule(str(schedule.get("frequency") or "daily"))
    if rrule:
        body["recurrence"] = [rrule]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    event_id = schedule.get("calendar_event_id")
    with httpx.Client(timeout=30.0) as client:
        if event_id:
            resp = client.patch(
                f"{CAL_URL}/{event_id}",
                headers=headers,
                json=body,
            )
            if resp.status_code == 404:
                event_id = None
            else:
                resp.raise_for_status()
                return str(resp.json().get("id") or event_id)
        resp = client.post(CAL_URL, headers=headers, json=body)
        resp.raise_for_status()
        return str(resp.json()["id"])
