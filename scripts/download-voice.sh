#!/usr/bin/env bash
# Download a Piper TTS voice to ~/.local/share/jarvis/voices/
# Usage: scripts/download-voice.sh [voice-name]     (default: en_US-amy-medium)
# Browse voices + samples: https://rhasspy.github.io/piper-samples/
set -euo pipefail

VOICE="${1:-en_US-amy-medium}"
DIR="${XDG_DATA_HOME:-$HOME/.local/share}/jarvis/voices"
mkdir -p "$DIR"

IFS='-' read -r LOCALE NAME QUALITY <<<"$VOICE"
LANG_CODE="${LOCALE%%_*}"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/$LANG_CODE/$LOCALE/$NAME/$QUALITY/$VOICE"

echo "Downloading $VOICE ..."
curl -fL --progress-bar -o "$DIR/$VOICE.onnx" "$BASE.onnx?download=true"
curl -fL --progress-bar -o "$DIR/$VOICE.onnx.json" "$BASE.onnx.json?download=true"

echo "Saved to $DIR/$VOICE.onnx"
echo "If you picked a non-default voice, set speech.piper_voice in config.yaml."
