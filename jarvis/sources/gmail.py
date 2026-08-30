"""Unread-mail summary from Gmail (optional, off by default)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

QUERY = "in:inbox is:unread newer_than:1d"


@dataclass
class MailSummary:
    count: int
    examples: list[tuple[str, str]] = field(default_factory=list)  # (sender, subject)


def unread_summary(creds, max_examples: int = 3) -> MailSummary:
    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    response = (
        service.users()
        .messages()
        .list(userId="me", q=QUERY, maxResults=25)
        .execute()
    )
    messages = response.get("messages", [])
    count = response.get("resultSizeEstimate", len(messages))

    examples: list[tuple[str, str]] = []
    for ref in messages[:max_examples]:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=ref["id"],
                format="metadata",
                metadataHeaders=["From", "Subject"],
            )
            .execute()
        )
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        examples.append(
            (_sender_name(headers.get("from", "")), headers.get("subject", "").strip())
        )
    return MailSummary(count=count, examples=examples)


def _sender_name(raw: str) -> str:
    """Turn 'Anna Jansen <anna@example.com>' into 'Anna Jansen'."""
    match = re.match(r'\s*"?([^"<]+?)"?\s*<', raw)
    if match:
        return match.group(1).strip()
    return raw.split("@")[0].strip() or raw.strip()
