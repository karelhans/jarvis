"""Jarvis — a private, local-first voice assistant for one household.

Say "Hey Jarvis, what's on the schedule for today?" and get a spoken
briefing of your calendar, todos, weather, and mail.
"""

__version__ = "0.1.0"


class JarvisError(Exception):
    """A user-facing error with a friendly message and a suggested fix."""
