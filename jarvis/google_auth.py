"""Google OAuth for a single household: one desktop OAuth client, one token.

First run opens a browser to sign in; after that the saved token refreshes
itself. Only the scopes for sources enabled in the config are requested, so
enabling a new source (say gmail) later means re-running `jarvis auth`.
"""

from __future__ import annotations

import os

from jarvis import JarvisError
from jarvis.config import Config

SCOPE_URLS = {
    "calendar": "https://www.googleapis.com/auth/calendar.readonly",
    "tasks": "https://www.googleapis.com/auth/tasks.readonly",
    "gmail": "https://www.googleapis.com/auth/gmail.readonly",
}


def required_scopes(cfg: Config) -> list[str]:
    scopes = []
    if cfg.sources.calendar:
        scopes.append(SCOPE_URLS["calendar"])
    if cfg.sources.tasks:
        scopes.append(SCOPE_URLS["tasks"])
    if cfg.sources.gmail:
        scopes.append(SCOPE_URLS["gmail"])
    return scopes


def get_credentials(cfg: Config, interactive: bool = True):
    """Return valid Google credentials, running the OAuth flow if needed."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise JarvisError(
            "Google API libraries are not installed. From the repo, run: "
            'pip install -e "."'
        ) from exc

    scopes = required_scopes(cfg)
    if not scopes:
        raise JarvisError(
            "No Google sources are enabled in the config, nothing to authorize."
        )

    creds = None
    if cfg.google.token.is_file():
        try:
            creds = Credentials.from_authorized_user_file(str(cfg.google.token), scopes)
        except ValueError:
            creds = None  # token file predates a scope change; redo the flow

    if creds and not set(scopes) <= set(creds.scopes or []):
        creds = None  # a new source was enabled; redo the flow

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if creds and creds.valid:
        return creds

    if not interactive:
        raise JarvisError(
            "Google authorization needed. Run `jarvis auth` once (on a machine "
            "with a browser) and copy the token file if this box is headless."
        )

    if not cfg.google.credentials.is_file():
        raise JarvisError(
            f"OAuth client file not found: {cfg.google.credentials}\n"
            "Create a Desktop OAuth client in Google Cloud Console and save the "
            "downloaded JSON there (see README, step 0)."
        )

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(
        str(cfg.google.credentials), scopes
    )
    creds = flow.run_local_server(port=0)

    cfg.google.token.parent.mkdir(parents=True, exist_ok=True)
    cfg.google.token.write_text(creds.to_json(), encoding="utf-8")
    os.chmod(cfg.google.token, 0o600)
    return creds
