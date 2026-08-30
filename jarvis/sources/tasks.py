"""Open todos from Google Tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Todo:
    title: str
    due: date | None = None
    list_name: str = ""


def open_todos(creds) -> list[Todo]:
    """All uncompleted tasks across every task list, most urgent first."""
    from googleapiclient.discovery import build

    service = build("tasks", "v1", credentials=creds, cache_discovery=False)
    todos: list[Todo] = []
    lists = service.tasklists().list(maxResults=25).execute().get("items", [])
    for tasklist in lists:
        response = (
            service.tasks()
            .list(
                tasklist=tasklist["id"],
                showCompleted=False,
                showHidden=False,
                maxResults=100,
            )
            .execute()
        )
        for item in response.get("items", []):
            title = (item.get("title") or "").strip()
            if not title:  # the Tasks API keeps ghost entries with empty titles
                continue
            todos.append(
                Todo(
                    title=title,
                    due=_parse_due(item.get("due")),
                    list_name=tasklist.get("title", ""),
                )
            )

    far_future = date.max
    todos.sort(key=lambda t: t.due or far_future)
    return todos


def _parse_due(raw: str | None) -> date | None:
    if not raw:
        return None
    # Google Tasks due dates look like "2026-08-30T00:00:00.000Z" (date-only).
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None
