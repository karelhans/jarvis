"""Today's events from Google Calendar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta


@dataclass
class Event:
    title: str
    start: datetime | None  # None for all-day events
    all_day: bool = False
    location: str = ""


def todays_events(creds, calendars: list[str], now: datetime) -> list[Event]:
    """Fetch today's events from the given calendar ids, sorted for speaking."""
    from googleapiclient.discovery import build

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    day_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
    day_end = day_start + timedelta(days=1)

    events: list[Event] = []
    for calendar_id in calendars:
        response = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            )
            .execute()
        )
        for item in response.get("items", []):
            event = _parse_item(item)
            if event:
                events.append(event)

    events.sort(key=lambda e: (not e.all_day, e.start or datetime.min.replace(tzinfo=now.tzinfo)))
    return events


def _parse_item(item: dict) -> Event | None:
    if item.get("status") == "cancelled":
        return None
    title = (item.get("summary") or "").strip() or "(untitled event)"
    start_raw = item.get("start", {})
    location = (item.get("location") or "").strip()
    if "dateTime" in start_raw:
        start = datetime.fromisoformat(start_raw["dateTime"].replace("Z", "+00:00"))
        return Event(title=title, start=start, all_day=False, location=location)
    if "date" in start_raw:
        return Event(title=title, start=None, all_day=True, location=location)
    return None
