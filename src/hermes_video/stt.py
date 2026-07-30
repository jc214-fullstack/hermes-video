"""Local faster-whisper STT adapter. Degrades gracefully when unavailable."""
from __future__ import annotations

import os
from importlib.util import find_spec
from pathlib import Path


def whisper_available() -> bool:
    return find_spec("faster_whisper") is not None


def transcribe_audio(audio_path: str | Path, *, model_size: str | None = None) -> tuple[list[dict], str]:
    """Transcribe audio with local faster-whisper.

    Returns ``(segments, status)`` where status is ``"stt"`` on success or a
    reason string (``"unavailable"``, ``"error:..."``) on failure. Never raises.
    """
    if not whisper_available():
        return [], "unavailable"
    audio = Path(audio_path)
    if not audio.exists():
        return [], "error:audio_missing"
    size = model_size or os.environ.get("HERMES_VIDEO_WHISPER_MODEL", "tiny")
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(size, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(str(audio), vad_filter=True)
        out = [
            {"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
            for s in segments
            if s.text.strip()
        ]
        return out, "stt"
    except Exception as exc:  # model download offline, backend crash, etc.
        return [], f"error:{type(exc).__name__}"
