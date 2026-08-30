# Jarvis

A private, local-first voice assistant for one household. The goal:

> **"Morning Jarvis — what's on the schedule for today? And anything else I need to know?"**

...and Jarvis answers out loud with today's calendar, open todos, the weather,
and (optionally) unread email. Speech recognition and the wake word run
entirely on your own machine; the only things it talks to are Google's APIs
for *your* data and Open-Meteo for the weather.

```
        "Hey Jarvis, what's on the schedule for today?"
            │
   mic ──▶ openWakeWord ──▶ record ──▶ faster-whisper ──▶ intent match
   (wake word, local)       (until     (speech-to-text,        │
                            silence)    local)                 ▼
   speaker ◀── Piper / say ◀─────────────────── briefing composer
               (text-to-speech)                        │
                              Google Calendar · Google Tasks · Gmail · Open-Meteo
```

`index.html` and `privacy.html` in this repo are the homepage and privacy
policy for the Google OAuth consent screen (host them, e.g. with GitHub
Pages, and link them in the consent screen settings).

## What you need

- **To develop and try it:** any laptop with a mic (macOS or Linux), Python 3.10+.
- **For the bedroom:** a Raspberry Pi 4/5 (2 GB is fine) with a USB
  speakerphone (one device that is both mic and speaker, e.g. a Jabra or
  Anker conference puck), or any always-on machine with a mic and speaker.

## The path, step by step

Each step works on its own, so you always know which layer broke.

### Step 0 — Google Cloud (one time, ~15 minutes)

You've already made the consent-screen pages; this wires them up.

1. Go to [console.cloud.google.com](https://console.cloud.google.com), create a project (e.g. "Jarvis").
2. **APIs & Services → Library**: enable **Google Calendar API** and
   **Google Tasks API** (and **Gmail API** only if you'll turn mail on).
3. **OAuth consent screen**: External, app name "Jarvis", your email;
   set the homepage and privacy-policy URLs to wherever `index.html` and
   `privacy.html` are hosted; add yourself as a **test user**.
4. **Credentials → Create credentials → OAuth client ID → Desktop app**,
   download the JSON and save it as `~/.config/jarvis/credentials.json`.

> **Gotcha worth knowing:** while the consent screen is in *Testing* mode,
> Google expires the token after 7 days, so Jarvis asks you to re-auth
> weekly. Once everything works, hit **Publish app** ("In production").
> With only the calendar/tasks read-only scopes that needs no verification
> review — you'll just click through an "unverified app" warning once, and
> the token stops expiring. (Gmail is a *restricted* scope: leaving
> `gmail: false` keeps publishing simple, which is why it's off by default.)

### Step 1 — install

```bash
git clone https://github.com/karelhans/jarvis ~/jarvis && cd ~/jarvis
python3 -m venv .venv && source .venv/bin/activate

pip install -e ".[voice]"          # macOS (TTS uses the built-in `say`)
pip install -e ".[voice,piper]"    # Linux / Raspberry Pi (adds Piper TTS)

cp config.example.yaml config.yaml # then edit: your name, city, coordinates
```

Extra system packages: macOS `brew install portaudio`; Raspberry Pi / Debian
`sudo apt install libportaudio2 alsa-utils`.

### Step 2 — hear the shape of it (no setup needed)

```bash
jarvis brief --demo
```

This prints a briefing built from sample data — proof the composer works
before any account is connected.

### Step 3 — connect Google

```bash
jarvis auth
```

A browser opens, you sign in, and a read-only token is stored at
`~/.config/jarvis/token.json`. Jarvis only ever *reads* your data.

### Step 4 — your first real briefing

```bash
jarvis brief
```

Today's actual events, todos, and weather, as text. If a source is
unreachable, the briefing says so in one calm sentence instead of crashing.

### Step 5 — give it a voice

```bash
scripts/download-voice.sh     # Linux/Pi: fetch a Piper voice (skip on macOS)
jarvis speak "Good morning, Karel."
jarvis brief --speak          # the real briefing, out loud
```

TTS picks the best available engine automatically: Piper → macOS `say` →
espeak → plain text.

### Step 6 — give it ears

```bash
jarvis hear
```

Records 5 seconds and prints what it understood, plus your mic level —
this is where you tune `silence_rms` or pick a `mic_device` if needed.
First run downloads the speech model (~75 MB for `base.en`).

### Step 7 — the goal

```bash
jarvis listen
```

Say **"Hey Jarvis, what's on the schedule for today? And anything else I
need to know?"** in one breath — recording starts the instant the wake word
fires. It also understands narrower asks: "what's on my todo list", "will
it rain today", "any new email", "what time is it", "thank you".

### Step 8 — make it permanent

On the Pi (or any Linux box), run it as a service that starts at boot:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/jarvis.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now jarvis
loginctl enable-linger $USER          # keep it alive when logged out
journalctl --user -u jarvis -f        # watch the logs
```

Bonus: have Jarvis speak *unprompted* when your alarm goes off —

```cron
# crontab -e : weekdays at 07:15
15 7 * * 1-5 XDG_RUNTIME_DIR=/run/user/1000 $HOME/jarvis/.venv/bin/jarvis brief --speak
```

## Saying literally "Morning, Jarvis"

The bundled openWakeWord model listens for **"Hey Jarvis"**. To answer to a
phrase of your own, train a custom model with openWakeWord's synthetic-data
notebook (see [dscripka/openWakeWord](https://github.com/dscripka/openWakeWord),
"Training New Models" — it runs in Colab and takes about an hour), then
point the config at the result:

```yaml
speech:
  wake_models: [~/.local/share/jarvis/morning_jarvis.onnx]
```

## Configuration

Everything lives in one YAML file — see
[`config.example.yaml`](config.example.yaml) for all keys with comments.
Jarvis looks for `./config.yaml`, then `~/.config/jarvis/config.yaml`
(override with `jarvis -c path` or `$JARVIS_CONFIG`).

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Voice packages missing` | `pip install -e ".[voice]"` inside the venv |
| No/wrong microphone | `python3 -m sounddevice` lists devices; set `speech.mic_device` |
| Wake word won't trigger | lower `speech.wake_threshold` to 0.4; check level with `jarvis hear` |
| Triggers on TV/random noise | raise `speech.wake_threshold` to 0.6–0.7 |
| Asks to re-auth every week | publish the OAuth app to production (step 0 gotcha) |
| Changed `sources:` in config | `jarvis auth --reset` to grant the new scopes |
| Slow on a Pi | use `stt_model: tiny.en` and a `low`-quality Piper voice |
| Cron briefing is silent | keep the `XDG_RUNTIME_DIR` env shown above |

## Development

```bash
python3 -m unittest discover -s tests    # no audio or network needed
```

## Where this can go next

- Route unmatched questions to an LLM so "anything else I need to know?"
  can pull in news, or answer follow-ups conversationally.
- More sources: transit delays for your first meeting, package tracking.
- Dutch: faster-whisper is multilingual, Piper has `nl_NL` voices — the
  intent keywords are the only English-only part.
- Home Assistant: expose `jarvis brief` as a service and let it speak on
  any speaker in the house.
