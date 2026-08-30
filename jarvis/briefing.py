"""Gather today's data and compose it into one speakable briefing.

Every sentence here is written to be *heard*, not read: short clauses,
no symbols a text-to-speech engine would stumble over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from jarvis.config import Config
from jarvis.sources.calendar import Event
from jarvis.sources.gmail import MailSummary
from jarvis.sources.tasks import Todo
from jarvis.sources.weather import Weather

_SMALL_NUMBERS = [
    "zero", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten",
]


@dataclass
class BriefingData:
    now: datetime
    events: list[Event] | None = None  # None means: source off or unavailable
    todos: list[Todo] | None = None
    weather: Weather | None = None
    mail: MailSummary | None = None
    problems: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- gathering

def gather(
    cfg: Config,
    demo: bool = False,
    only: set[str] | None = None,
    interactive: bool = True,
) -> BriefingData:
    """Fetch data from every enabled source; failures become a spoken note.

    With interactive=True a missing Google token triggers the browser OAuth
    flow; the voice loop passes False so it fails fast with a spoken hint
    instead of silently waiting on a browser.
    """
    now = cfg.now()
    data = BriefingData(now=now)

    if demo:
        from jarvis.sources import demo as demo_src

        data.events = demo_src.demo_events(now)
        data.todos = demo_src.demo_todos(now)
        data.weather = demo_src.demo_weather()
        data.mail = demo_src.demo_mail()
        return data

    def wanted(name: str) -> bool:
        return only is None or name in only

    creds = None
    needs_google = (
        (cfg.sources.calendar and wanted("calendar"))
        or (cfg.sources.tasks and wanted("tasks"))
        or (cfg.sources.gmail and wanted("gmail"))
    )
    if needs_google:
        from jarvis import google_auth

        creds = google_auth.get_credentials(cfg, interactive=interactive)

    if cfg.sources.calendar and wanted("calendar"):
        try:
            from jarvis.sources import calendar as cal_src

            data.events = cal_src.todays_events(creds, cfg.google.calendars, now)
        except Exception:
            data.problems.append("I couldn't reach your calendar.")

    if cfg.sources.tasks and wanted("tasks"):
        try:
            from jarvis.sources import tasks as tasks_src

            data.todos = tasks_src.open_todos(creds)
        except Exception:
            data.problems.append("I couldn't reach your todo list.")

    if cfg.sources.gmail and wanted("gmail"):
        try:
            from jarvis.sources import gmail as gmail_src

            data.mail = gmail_src.unread_summary(creds)
        except Exception:
            data.problems.append("I couldn't check your email.")

    if cfg.sources.weather and wanted("weather"):
        try:
            from jarvis.sources import weather as weather_src

            data.weather = weather_src.fetch(cfg.location)
        except Exception:
            data.problems.append("I couldn't get the weather.")

    return data


# ---------------------------------------------------------------- composing

def compose(cfg: Config, data: BriefingData) -> str:
    """The full morning briefing, one paragraph per topic."""
    parts = [greeting(cfg, data.now)]
    if data.weather is not None:
        parts.append(section_weather(data.weather))
    if data.events is not None:
        parts.append(section_events(cfg, data.events))
    if data.todos is not None:
        parts.append(section_todos(data.todos, data.now))
    if data.mail is not None:
        parts.append(section_mail(data.mail))
    parts.extend(data.problems)
    parts.append(closer(data.now))
    return "\n".join(p for p in parts if p)


def greeting(cfg: Config, now: datetime) -> str:
    name = f", {cfg.owner}" if cfg.owner else ""
    return (
        f"Good {_part_of_day(now)}{name}. "
        f"It's {_date_phrase(now)}, {speakable_time(now, cfg.time_format)}."
    )


def closer(now: datetime) -> str:
    return f"That's everything. Have a good {_part_of_day(now)}."


def section_weather(w: Weather) -> str:
    bits = []
    place = f" in {w.city}" if w.city else ""
    lead = f"{w.description.capitalize()}{place}"
    temps = []
    if w.temp_now is not None:
        temps.append(f"{round(w.temp_now)} degrees right now")
    if w.temp_high is not None and w.temp_low is not None:
        temps.append(f"a high of {round(w.temp_high)} and a low of {round(w.temp_low)}")
    elif w.temp_high is not None:
        temps.append(f"a high of {round(w.temp_high)}")
    if temps:
        lead += ", with " + " and ".join(temps)
    bits.append(lead + ".")
    if w.precip_prob is not None and w.precip_prob >= 40:
        bits.append(
            f"There's a {w.precip_prob} percent chance of rain, "
            "so maybe take a jacket."
        )
    return " ".join(bits)


def section_events(cfg: Config, events: list[Event]) -> str:
    if not events:
        return "Your calendar is clear today."
    lines = [f"You have {_count(len(events), 'thing', 'things')} on the calendar."]
    for event in events:
        if event.all_day:
            line = f"All day: {event.title}"
        else:
            line = f"At {speakable_time(event.start, cfg.time_format)}, {event.title}"
        if event.location and len(event.location) <= 30:
            line += f", at {event.location}"
        lines.append(line + ".")
    return " ".join(lines)


def section_todos(todos: list[Todo], now: datetime) -> str:
    if not todos:
        return "Your todo list is empty."
    today = now.date()
    overdue = [t for t in todos if t.due and t.due < today]
    due_today = [t for t in todos if t.due == today]
    rest = [t for t in todos if t not in overdue and t not in due_today]

    lines = [f"You have {_count(len(todos), 'open todo', 'open todos')}."]
    if overdue:
        lines.append(
            f"{_count(len(overdue), 'is overdue', 'are overdue').capitalize()}: "
            f"{_join([t.title for t in overdue])}."
        )
    if due_today:
        lines.append(f"Due today: {_join([t.title for t in due_today])}.")
    if rest and len(overdue) + len(due_today) < 5:
        shown = rest[:3]
        line = f"Also on the list: {_join([t.title for t in shown])}"
        if len(rest) > len(shown):
            line += f", and {_count(len(rest) - len(shown), 'more', 'more')}"
        lines.append(line + ".")
    return " ".join(lines)


def section_mail(mail: MailSummary) -> str:
    if mail.count == 0:
        return "No new email since yesterday."
    line = f"{_count(mail.count, 'unread email', 'unread emails').capitalize()} since yesterday"
    if mail.examples:
        sender, subject = mail.examples[0]
        line += f". The latest is from {sender}"
        if subject:
            line += f", about: {subject}"
    if line[-1] not in ".!?":
        line += "."
    return line


# ------------------------------------------------------------------ helpers

def speakable_time(dt: datetime | None, time_format: str = "24h") -> str:
    if dt is None:
        return "some time"
    if time_format == "12h":
        hour = dt.hour % 12 or 12
        suffix = "AM" if dt.hour < 12 else "PM"
        if dt.minute == 0:
            return f"{hour} {suffix}"
        return f"{hour}:{dt.minute:02d} {suffix}"
    return f"{dt.hour}:{dt.minute:02d}"


def _part_of_day(now: datetime) -> str:
    if now.hour < 12:
        return "morning"
    if now.hour < 18:
        return "afternoon"
    return "evening"


def _date_phrase(now: datetime) -> str:
    return f"{now.strftime('%A')} the {_ordinal(now.day)} of {now.strftime('%B')}"


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _count(n: int, singular: str, plural: str) -> str:
    word = _SMALL_NUMBERS[n] if 0 <= n <= 10 else str(n)
    return f"{word} {singular if n == 1 else plural}"


def _join(items: list[str]) -> str:
    items = [i.rstrip(".") for i in items]
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
