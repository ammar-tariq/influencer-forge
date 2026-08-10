from forge_python.calendar_sync import _rrule, google_auth_url


def test_google_auth_url_contains_scope() -> None:
    url = google_auth_url("cid.apps.googleusercontent.com", redirect_uri="http://127.0.0.1:8765/cb")
    assert "accounts.google.com" in url
    assert "calendar.events" in url
    assert "cid.apps.googleusercontent.com" in url


def test_rrule_frequencies() -> None:
    assert _rrule("daily") == "RRULE:FREQ=DAILY"
    assert _rrule("weekly") == "RRULE:FREQ=WEEKLY"
    assert _rrule("monthly") == "RRULE:FREQ=MONTHLY"
