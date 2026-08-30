"""Map a transcribed sentence to what the user wants.

Deliberately simple keyword matching: for a one-household assistant with a
handful of commands, rules beat a model — instant, offline, predictable.
Order matters: specific intents are checked before the broad briefing one.
"""

from __future__ import annotations

import re
from enum import Enum


class Intent(Enum):
    BRIEF = "brief"       # the full morning briefing
    TODOS = "todos"       # just the todo list
    WEATHER = "weather"   # just the weather
    MAIL = "mail"         # just unread email
    TIME = "time"         # just the clock
    THANKS = "thanks"
    STOP = "stop"
    UNKNOWN = "unknown"


_RULES: list[tuple[Intent, tuple[str, ...]]] = [
    (Intent.THANKS, ("thank you", "thanks", "cheers")),
    (Intent.STOP, ("never mind", "nevermind", "stop", "cancel", "nothing", "go to sleep")),
    (Intent.TIME, ("what time", "the time", "what's the time")),
    (Intent.WEATHER, ("weather", "temperature", "forecast", "rain", "umbrella", "jacket")),
    (Intent.MAIL, ("email", "e-mail", "mail", "inbox")),
    (Intent.TODOS, ("todo", "to-do", "to do", "task")),
    (
        Intent.BRIEF,
        (
            "schedule", "briefing", "brief", "agenda", "calendar", "my day",
            "anything else", "need to know", "should know", "what's happening",
            "whats happening", "plan for today", "on today", "coming up",
            "appointments", "meetings", "morning", "update", "updates",
        ),
    ),
]


def detect(text: str) -> Intent:
    normalized = " " + re.sub(r"[^a-z0-9' -]", " ", text.lower()) + " "
    normalized = re.sub(r"\s+", " ", normalized)
    for intent, phrases in _RULES:
        for phrase in phrases:
            if phrase in normalized:
                return intent
    return Intent.UNKNOWN
