"""Microphone streaming and wake-word detection (openWakeWord).

The bundled "hey_jarvis" model listens for "Hey Jarvis". You can point
`speech.wake_models` at a custom .onnx model instead (see README) if you
want it to answer to literally "Morning, Jarvis".
"""

from __future__ import annotations

import queue

from jarvis import JarvisError
from jarvis.config import Config

SAMPLE_RATE = 16000
CHUNK = 1280  # 80 ms frames — openWakeWord's preferred size
CHUNK_SECONDS = CHUNK / SAMPLE_RATE

_INSTALL_HINT = 'Voice packages missing. Run: pip install -e ".[voice]"'


class Microphone:
    """Streams 16 kHz mono int16 chunks from the configured input device."""

    def __init__(self, cfg: Config):
        try:
            import sounddevice as sd
        except Exception as exc:  # ImportError, or PortAudio missing
            raise JarvisError(
                _INSTALL_HINT + " (and on Linux: sudo apt install libportaudio2)"
            ) from exc
        self._queue: queue.Queue = queue.Queue()
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=CHUNK,
            device=cfg.speech.mic_device,
            callback=self._on_audio,
        )

    def _on_audio(self, indata, frames, time_info, status) -> None:
        self._queue.put(indata[:, 0].copy())

    def __enter__(self) -> "Microphone":
        self._stream.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self._stream.stop()
        self._stream.close()

    def read(self, timeout: float = 2.0):
        """Next 80 ms chunk as an int16 numpy array (raises queue.Empty)."""
        return self._queue.get(timeout=timeout)

    def drain(self) -> None:
        """Throw away buffered audio (e.g. Jarvis's own voice)."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return


def load_model(cfg: Config):
    """Load the wake-word model, downloading the pretrained files on first run."""
    try:
        from openwakeword.model import Model
    except ImportError as exc:
        raise JarvisError(_INSTALL_HINT) from exc

    kwargs = dict(
        wakeword_models=list(cfg.speech.wake_models),
        inference_framework="onnx",
    )
    try:
        return Model(**kwargs)
    except Exception:
        # First run: fetch openWakeWord's pretrained model files, then retry.
        import openwakeword.utils

        print("Downloading wake-word models (first run only)...")
        openwakeword.utils.download_models()
        return Model(**kwargs)


def detected(model, chunk, threshold: float) -> bool:
    scores = model.predict(chunk)
    return bool(scores) and max(scores.values()) >= threshold
