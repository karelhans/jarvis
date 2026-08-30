"""Canned sample data so `jarvis brief --demo` works with no setup at all."""

from __future__ import annotations

from datetime import datetime, timedelta

from jarvis.sources.calendar import Event
from jarvis.sources.gmail import MailSummary
from jarvis.sources.tasks import Todo
from jarvis.sources.weather import Weather


def demo_events(now: datetime) -> list[Event]:
    def at(hour: int, minute: int) -> datetime:
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return [
        Event(title="Recycling pickup", start=None, all_day=True),
        Event(title="Standup with the team", start=at(9, 30)),
        Event(title="Lunch with Anna", start=at(12, 30), location="De Pijp"),
        Event(title="Padel", start=at(19, 0)),
    ]


def demo_todos(now: datetime) -> list[Todo]:
    today = now.date()
    return [
        Todo(title="Renew passport", due=today - timedelta(days=2)),
        Todo(title="Pay water bill", due=today),
        Todo(title="Book dentist appointment", due=today),
        Todo(title="Fix the shed door", due=None),
        Todo(title="Order birthday present for mom", due=None),
    ]


def demo_weather() -> Weather:
    return Weather(
        description="partly cloudy",
        temp_now=14.2,
        temp_high=19.0,
        temp_low=11.0,
        precip_prob=60,
        city="Amsterdam",
    )


def demo_mail() -> MailSummary:
    return MailSummary(
        count=4,
        examples=[
            ("Anna Jansen", "Lunch today?"),
            ("Bol.com", "Your order has shipped"),
        ],
    )
