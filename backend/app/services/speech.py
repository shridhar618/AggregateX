"""Local speech-to-text for witness dictation (faster-whisper on CPU).

Audio is transcribed on this machine and never sent to a third-party service.
Optional: when faster-whisper is not installed, dictation falls back to the
browser's own speech recognition.
"""

from __future__ import annotations

import io
import os
import threading

MODEL = os.environ.get("REVELIO_WHISPER_MODEL", "base.en")
MODEL_DIR = os.environ.get("REVELIO_WHISPER_DIR") or None
# Set when the model is baked into the image, so nothing is downloaded at runtime.
OFFLINE = os.environ.get("REVELIO_WHISPER_OFFLINE", "") == "1"
MAX_AUDIO_BYTES = 15 * 1024 * 1024

_model = None
_lock = threading.Lock()  # one transcription at a time keeps CPU and memory bounded


def status() -> dict:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return {"available": False, "reason": "faster-whisper is not installed on the server."}
    return {"available": True, "engine": "faster-whisper", "model": MODEL, "runs_locally": True}


def transcribe(audio: bytes, language: str | None = None) -> str:
    from faster_whisper import WhisperModel

    global _model
    with _lock:
        if _model is None:
            _model = WhisperModel(MODEL, device="cpu", compute_type="int8",
                                  download_root=MODEL_DIR, local_files_only=OFFLINE)
        try:
            segments, _ = _model.transcribe(io.BytesIO(audio), language=language, beam_size=1,
                                            vad_filter=True, condition_on_previous_text=False)
            return " ".join(s.text.strip() for s in segments).strip()
        except Exception as exc:  # undecodable or empty recordings
            if type(exc).__module__.startswith("av"):
                raise ValueError("The recording could not be decoded. Try again.") from None
            raise
