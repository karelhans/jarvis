"""Speech-to-text with faster-whisper, fully local."""

from __future__ import annotations

from jarvis import JarvisError
from jarvis.config import Config

_model = None
_model_name = None


def preload(cfg: Config) -> None:
    """Load (and on first run, download) the model before it's needed."""
    _load(cfg)


def transcribe(audio, cfg: Config) -> str:
    """Transcribe mono float32 audio at 16 kHz (a numpy array) to text."""
    model = _load(cfg)
    language = cfg.speech.language or None
    if cfg.speech.stt_model.endswith(".en"):
        language = "en"
    segments, _info = model.transcribe(
        audio,
        language=language,
        beam_size=3,
        vad_filter=True,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def _load(cfg: Config):
    global _model, _model_name
    if _model is not None and _model_name == cfg.speech.stt_model:
        return _model
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise JarvisError(
            "faster-whisper is not installed. Run: pip install -e \".[voice]\""
        ) from exc
    _model = WhisperModel(cfg.speech.stt_model, device="cpu", compute_type="int8")
    _model_name = cfg.speech.stt_model
    return _model
