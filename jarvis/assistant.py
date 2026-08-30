"""The always-on voice loop: wake word → listen → understand → answer.

Say "Hey Jarvis, what's on the schedule for today?" in one breath —
recording starts the moment the wake word fires, so the rest of the
sentence is captured. If you only say the wake word, Jarvis answers
with a short acknowledgement and listens again.
"""

from __future__ import annotations

import queue

from jarvis import JarvisError, briefing
from jarvis.config import Config
from jarvis.intents import Intent, detect
from jarvis.speech import stt, tts, wake

_SILENCE_TO_STOP = 0.9  # seconds of quiet that ends a command
_GIVE_UP_AFTER = 3.0    # seconds with no speech at all


def run(cfg: Config) -> None:
    model = wake.load_model(cfg)
    print("Loading the speech recognizer (downloads the model on first run)...")
    stt.preload(cfg)

    names = ", ".join(cfg.speech.wake_models)
    print(f"Jarvis is listening for: {names}. Say the wake word, then ask")
    print('for example: "what\'s on the schedule for today?"  (Ctrl+C quits)')

    with wake.Microphone(cfg) as mic:
        while True:
            try:
                chunk = mic.read()
            except queue.Empty:
                continue
            if not wake.detected(model, chunk, cfg.speech.wake_threshold):
                continue

            print("* wake word heard")
            text = _capture_command(mic, cfg)
            model.reset()
            if not text and cfg.speech.ack:
                _say(cfg.speech.ack, cfg)
                mic.drain()
                text = _capture_command(mic, cfg)
                model.reset()

            if text:
                print(f'  you said: "{text}"')
                _say(respond(text, cfg), cfg)
            else:
                print("  (heard nothing)")
            mic.drain()
            model.reset()


def _capture_command(mic: wake.Microphone, cfg: Config) -> str:
    audio = _record(mic, cfg)
    if audio is None:
        return ""
    return stt.transcribe(audio, cfg)


def _record(mic: wake.Microphone, cfg: Config):
    """Record until ~a second of silence follows speech; None if nothing said."""
    import numpy as np

    chunks = []
    heard_speech = False
    silence = 0.0
    elapsed = 0.0
    while elapsed < cfg.speech.max_command_seconds:
        try:
            chunk = mic.read(timeout=2.0)
        except queue.Empty:
            break
        chunks.append(chunk)
        elapsed += wake.CHUNK_SECONDS
        rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
        if rms >= cfg.speech.silence_rms:
            heard_speech = True
            silence = 0.0
        elif heard_speech:
            silence += wake.CHUNK_SECONDS
            if silence >= _SILENCE_TO_STOP:
                break
        elif elapsed >= _GIVE_UP_AFTER:
            return None
    if not heard_speech:
        return None
    return np.concatenate(chunks).astype(np.float32) / 32768.0


def respond(text: str, cfg: Config) -> str:
    """Turn a transcribed command into the sentence Jarvis should say."""
    intent = detect(text)
    try:
        if intent is Intent.BRIEF:
            data = briefing.gather(cfg, interactive=False)
            return briefing.compose(cfg, data)
        if intent is Intent.TODOS:
            data = briefing.gather(cfg, only={"tasks"}, interactive=False)
            if data.todos is None:
                return data.problems[0] if data.problems else "The todo source is turned off."
            return briefing.section_todos(data.todos, data.now)
        if intent is Intent.WEATHER:
            data = briefing.gather(cfg, only={"weather"}, interactive=False)
            if data.weather is None:
                return data.problems[0] if data.problems else "The weather source is turned off."
            return briefing.section_weather(data.weather)
        if intent is Intent.MAIL:
            if not cfg.sources.gmail:
                return "Email is turned off in my config."
            data = briefing.gather(cfg, only={"gmail"}, interactive=False)
            if data.mail is None:
                return data.problems[0] if data.problems else "I couldn't check your email."
            return briefing.section_mail(data.mail)
        if intent is Intent.TIME:
            return f"It's {briefing.speakable_time(cfg.now(), cfg.time_format)}."
        if intent is Intent.THANKS:
            return "You're welcome."
        if intent is Intent.STOP:
            return "Okay."
    except JarvisError as exc:
        print(exc)
        return str(exc).splitlines()[0]
    return (
        f"I heard: {text}. I can't do that yet. "
        "Try asking: what's on the schedule for today?"
    )


def _say(message: str, cfg: Config) -> None:
    print("  jarvis:", message.replace("\n", "\n          "))
    tts.speak(message, cfg)
