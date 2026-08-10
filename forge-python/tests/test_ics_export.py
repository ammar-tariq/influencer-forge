from datetime import datetime

from forge_python.ics_export import build_calendar, build_vevent


def test_build_vevent_daily_rrule() -> None:
    now = datetime(2026, 8, 10, 8, 0, 0)
    lines = build_vevent(
        {
            "id": 3,
            "influencer_id": 1,
            "schedule_time": "09:30:00",
            "frequency": "daily",
            "prompt_template": "morning coffee, soft light",
            "is_active": 1,
        },
        influencer_name="Nova",
        now=now,
    )
    joined = "\n".join(lines)
    assert "UID:iforge-schedule-3@localhost" in joined
    assert "DTSTART:20260810T093000" in joined
    assert "RRULE:FREQ=DAILY" in joined
    assert "SUMMARY:InfluencerForge: Nova" in joined
    assert "morning coffee" in joined


def test_build_calendar_skips_inactive() -> None:
    ics = build_calendar(
        [
            {
                "id": 1,
                "influencer_id": 9,
                "schedule_time": "10:00:00",
                "frequency": "weekly",
                "prompt_template": "active one",
                "is_active": 1,
            },
            {
                "id": 2,
                "influencer_id": 9,
                "schedule_time": "11:00:00",
                "frequency": "daily",
                "prompt_template": "paused",
                "is_active": 0,
            },
        ],
        names={9: "Elena"},
        now=datetime(2026, 8, 10, 7, 0, 0),
    )
    assert "BEGIN:VCALENDAR" in ics
    assert "FREQ=WEEKLY" in ics
    assert "active one" in ics
    assert "paused" not in ics
    assert ics.endswith("\r\n")
