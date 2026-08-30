"""Text-to-speech with a graceful fallback chain.

Preference order on "auto":
  1. piper   — local neural voice, best quality (Linux / Raspberry Pi / macOS)
  2. say     — macOS built-in
  3. espeak  — espeak-ng, robotic but everywhere
  4. print   — no audio available; text goes to the terminal
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jarvis.config import Config


def speak(text: str, cfg: Config) -> None:
    engine = cfg.speech.tts_engine
    if engine == "auto":
        for candidate in ("piper", "say", "espeak", "print"):
            if _try(candidate, text, cfg):
                return
    else:
        if _try(engine, text, cfg):
            return
        print(f"(tts engine {engine!r} failed, falling back to text)", file=sys.stderr)
    _print_engine(text)


def _try(engine: str, text: str, cfg: Config) -> bool:
    try:
        if engine == "piper":
            return _piper(text, cfg)
        if engine == "say":
            return _say(text)
        if engine == "espeak":
            return _espeak(text)
        if engine == "print":
            _print_engine(text)
            return True
    except Exception:
        return False
    return False


def _piper(text: str, cfg: Config) -> bool:
    voice = cfg.speech.piper_voice
    piper = shutil.which("piper")
    if not piper or not Path(voice).is_file():
        return False
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    try:
        result = subprocess.run(
            [piper, "--model", str(voice), "--output_file", wav_path],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            return False
        return _play_wav(wav_path)
    finally:
        Path(wav_path).unlink(missing_ok=True)


def _say(text: str) -> bool:
    if sys.platform != "darwin" or not shutil.which("say"):
        return False
    subprocess.run(["say", text], check=True, timeout=300)
    return True


def _espeak(text: str) -> bool:
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        return False
    subprocess.run([binary, "-s", "165", text], check=True, timeout=300,
                   capture_output=True)
    return True


def _play_wav(path: str) -> bool:
    for player, args in (
        ("afplay", []),
        ("paplay", []),
        ("aplay", ["-q"]),
        ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
    ):
        binary = shutil.which(player)
        if binary:
            subprocess.run([binary, *args, path], check=True, timeout=300,
                           capture_output=True)
            return True
    # Last resort: play through sounddevice if the voice extras are installed.
    try:
        import soundfile as sf
        import sounddevice as sd

        audio, samplerate = sf.read(path)
        sd.play(audio, samplerate)
        sd.wait()
        return True
    except Exception:
        return False


def _print_engine(text: str) -> None:
    print(f"[jarvis says] {text}")
