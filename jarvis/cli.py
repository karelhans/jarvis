"""Command line interface.

    jarvis brief --demo      the briefing with sample data (works instantly)
    jarvis auth              connect your Google account (one time)
    jarvis brief             today's real briefing, printed
    jarvis brief --speak     ...and spoken out loud
    jarvis speak "hello"     test text-to-speech
    jarvis hear              test the microphone + speech-to-text
    jarvis listen            the full "Hey Jarvis" voice loop
"""

from __future__ import annotations

import argparse
import sys

from jarvis import JarvisError, __version__


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        print()
        return 130
    except JarvisError as exc:
        print(f"jarvis: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="A private voice assistant that briefs you on your day.",
    )
    parser.add_argument("--version", action="version", version=f"jarvis {__version__}")
    parser.add_argument("-c", "--config", help="path to config.yaml", default=None)
    sub = parser.add_subparsers(dest="command")

    p_auth = sub.add_parser("auth", help="connect your Google account (one time)")
    p_auth.add_argument(
        "--reset", action="store_true", help="forget the saved token and reauthorize"
    )
    p_auth.set_defaults(func=cmd_auth)

    p_brief = sub.add_parser("brief", help="print (and optionally speak) the briefing")
    p_brief.add_argument("--speak", action="store_true", help="also say it out loud")
    p_brief.add_argument(
        "--demo", action="store_true", help="use sample data; needs no setup"
    )
    p_brief.set_defaults(func=cmd_brief)

    p_listen = sub.add_parser("listen", help="run the always-on wake-word loop")
    p_listen.set_defaults(func=cmd_listen)

    p_speak = sub.add_parser("speak", help="test text-to-speech")
    p_speak.add_argument("text", nargs="+", help="what to say")
    p_speak.set_defaults(func=cmd_speak)

    p_hear = sub.add_parser("hear", help="test the microphone and transcription")
    p_hear.add_argument(
        "--seconds", type=float, default=5.0, help="how long to record (default 5)"
    )
    p_hear.set_defaults(func=cmd_hear)

    return parser


def _load_config(args):
    from jarvis import config

    return config.load(args.config)


def cmd_auth(args) -> int:
    from jarvis import google_auth

    cfg = _load_config(args)
    if args.reset and cfg.google.token.is_file():
        cfg.google.token.unlink()
        print(f"Removed {cfg.google.token}")
    google_auth.get_credentials(cfg, interactive=True)
    scopes = google_auth.required_scopes(cfg)
    print("Authorized. Token saved to", cfg.google.token)
    print("Scopes:", ", ".join(s.rsplit("/", 1)[-1] for s in scopes))
    return 0


def cmd_brief(args) -> int:
    from jarvis import briefing

    cfg = _load_config(args)
    data = briefing.gather(cfg, demo=args.demo)
    text = briefing.compose(cfg, data)
    print(text)
    if args.speak:
        from jarvis.speech import tts

        tts.speak(text, cfg)
    return 0


def cmd_listen(args) -> int:
    from jarvis import assistant

    assistant.run(_load_config(args))
    return 0


def cmd_speak(args) -> int:
    from jarvis.speech import tts

    tts.speak(" ".join(args.text), _load_config(args))
    return 0


def cmd_hear(args) -> int:
    import queue

    cfg = _load_config(args)
    from jarvis.speech import stt, wake

    stt.preload(cfg)
    chunks = []
    total = 0.0
    print(f"Recording {args.seconds:.0f} seconds — say something...")
    with wake.Microphone(cfg) as mic:
        while total < args.seconds:
            try:
                chunks.append(mic.read())
                total += wake.CHUNK_SECONDS
            except queue.Empty:
                break
    if not chunks:
        raise JarvisError("No audio arrived from the microphone.")

    import numpy as np

    audio = np.concatenate(chunks).astype(np.float32) / 32768.0
    rms = float(np.sqrt(np.mean((audio * 32768.0) ** 2)))
    text = stt.transcribe(audio, cfg)
    print(f'Heard: "{text}"' if text else "Heard nothing.")
    print(f"(average level {rms:.0f}; silence_rms is {cfg.speech.silence_rms} — "
          "if speech stays below that, lower silence_rms in config.yaml)")
    return 0
