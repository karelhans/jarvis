"""Configuration loading.

Looks for a YAML config in this order:
  1. path given with --config / $JARVIS_CONFIG
  2. ./config.yaml (next to where you run jarvis)
  3. ~/.config/jarvis/config.yaml

Everything has a sensible default, so Jarvis also runs with no config at all
(demo mode needs nothing; real briefings need at least the Google credentials).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from pathlib import Path

from jarvis import JarvisError

DEFAULT_CONFIG_DIR = Path("~/.config/jarvis").expanduser()


@dataclass
class Location:
    city: str = ""
    latitude: float | None = None
    longitude: float | None = None
    units: str = "celsius"  # celsius | fahrenheit


@dataclass
class Sources:
    calendar: bool = True
    tasks: bool = True
    gmail: bool = False  # gmail.readonly is a restricted scope; opt in
    weather: bool = True


@dataclass
class Google:
    credentials: Path = DEFAULT_CONFIG_DIR / "credentials.json"
    token: Path = DEFAULT_CONFIG_DIR / "token.json"
    calendars: list[str] = field(default_factory=lambda: ["primary"])


@dataclass
class Speech:
    wake_models: list[str] = field(default_factory=lambda: ["hey_jarvis"])
    wake_threshold: float = 0.5
    ack: str = "Yes?"  # spoken when woken without a command; "" to disable
    stt_model: str = "base.en"  # faster-whisper size or path
    language: str = "en"
    tts_engine: str = "auto"  # auto | piper | say | espeak | print
    piper_voice: Path = Path(
        "~/.local/share/jarvis/voices/en_US-amy-medium.onnx"
    ).expanduser()
    mic_device: int | str | None = None
    silence_rms: int = 300
    max_command_seconds: float = 10.0


@dataclass
class Config:
    owner: str = ""
    timezone: str = ""  # IANA name; "" = machine's local timezone
    time_format: str = "24h"  # "12h" or "24h", used when speaking times
    location: Location = field(default_factory=Location)
    sources: Sources = field(default_factory=Sources)
    google: Google = field(default_factory=Google)
    speech: Speech = field(default_factory=Speech)

    def tz(self) -> tzinfo:
        if self.timezone:
            try:
                from zoneinfo import ZoneInfo

                return ZoneInfo(self.timezone)
            except Exception as exc:
                raise JarvisError(
                    f"Unknown timezone {self.timezone!r} in config; "
                    "use an IANA name like Europe/Amsterdam."
                ) from exc
        local = datetime.now().astimezone().tzinfo
        assert local is not None
        return local

    def now(self) -> datetime:
        return datetime.now(self.tz())


def _expand(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def load(path: str | None = None) -> Config:
    """Load config from `path`, $JARVIS_CONFIG, or the default locations."""
    candidates: list[Path] = []
    if path:
        candidates.append(_expand(path))
    elif os.environ.get("JARVIS_CONFIG"):
        candidates.append(_expand(os.environ["JARVIS_CONFIG"]))
    else:
        candidates += [Path("config.yaml"), DEFAULT_CONFIG_DIR / "config.yaml"]

    for candidate in candidates:
        if candidate.is_file():
            return _from_file(candidate)
    if path:  # an explicitly named file must exist
        raise JarvisError(f"Config file not found: {candidates[0]}")
    return Config()


def _from_file(path: Path) -> Config:
    try:
        import yaml  # lazy: only needed when a config file exists
    except ImportError as exc:
        raise JarvisError(
            f"Found {path} but PyYAML is not installed. "
            'Run: pip install -e "."'
        ) from exc

    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise JarvisError(f"{path} does not contain a YAML mapping.")
    return _from_dict(raw)


def _from_dict(raw: dict) -> Config:
    cfg = Config()
    cfg.owner = str(raw.get("owner", cfg.owner) or "")
    cfg.timezone = str(raw.get("timezone", cfg.timezone) or "")
    cfg.time_format = str(raw.get("time_format", cfg.time_format) or "24h")

    loc = raw.get("location") or {}
    cfg.location = Location(
        city=str(loc.get("city", "") or ""),
        latitude=_maybe_float(loc.get("latitude")),
        longitude=_maybe_float(loc.get("longitude")),
        units=str(loc.get("units", "celsius") or "celsius"),
    )

    src = raw.get("sources") or {}
    cfg.sources = Sources(
        calendar=bool(src.get("calendar", True)),
        tasks=bool(src.get("tasks", True)),
        gmail=bool(src.get("gmail", False)),
        weather=bool(src.get("weather", True)),
    )

    goo = raw.get("google") or {}
    cfg.google = Google(
        credentials=_expand(str(goo.get("credentials", cfg.google.credentials))),
        token=_expand(str(goo.get("token", cfg.google.token))),
        calendars=[str(c) for c in (goo.get("calendars") or ["primary"])],
    )

    sp = raw.get("speech") or {}
    defaults = Speech()
    ack_raw = sp.get("ack", defaults.ack)
    cfg.speech = Speech(
        wake_models=[str(m) for m in (sp.get("wake_models") or defaults.wake_models)],
        wake_threshold=float(sp.get("wake_threshold", defaults.wake_threshold)),
        ack="" if ack_raw is None else str(ack_raw),
        stt_model=str(sp.get("stt_model", defaults.stt_model)),
        language=str(sp.get("language", defaults.language)),
        tts_engine=str(sp.get("tts_engine", defaults.tts_engine)),
        piper_voice=_expand(str(sp.get("piper_voice", defaults.piper_voice))),
        mic_device=sp.get("mic_device"),
        silence_rms=int(sp.get("silence_rms", defaults.silence_rms)),
        max_command_seconds=float(
            sp.get("max_command_seconds", defaults.max_command_seconds)
        ),
    )
    return cfg


def _maybe_float(value) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
