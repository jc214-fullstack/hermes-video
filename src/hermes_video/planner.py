from __future__ import annotations

import re
from collections.abc import Iterable

from .models import DetailMode

CUE_RE = re.compile(
    r"\b(look at this|look here|as you can see|see here|this repo|this repository|this command|install|clone|github|website|tool|watch this|watch this part)\b",
    re.I,
)

_DETAIL_ALIASES = {
    "transcript": "quick",
    "quick": "quick",
    "efficient": "efficient",
    "fast": "efficient",
    "balanced": "balanced",
    "deep": "deep",
    "focused": "focused",
    "full": "full",
    "token-burner": "full",
    "token_burner": "full",
    "tokenburner": "full",
}


def normalize_detail_mode(detail: str | DetailMode) -> str:
    value = str(detail.value if isinstance(detail, DetailMode) else detail).strip().lower()
    if value not in _DETAIL_ALIASES:
        raise ValueError(f"unsupported detail mode: {detail}")
    return _DETAIL_ALIASES[value]


def select_detail_defaults(detail: str | DetailMode, *, focused: bool = False) -> dict[str, object]:
    mode = normalize_detail_mode(detail)
    if focused or mode == DetailMode.FOCUSED.value:
        return {"mode": "focused", "max_frames": 100, "strategy": "dense_range", "ocr": True}
    if mode == DetailMode.QUICK.value:
        return {"mode": "quick", "max_frames": 0, "strategy": "transcript_first", "ocr": False}
    if mode == DetailMode.EFFICIENT.value:
        return {"mode": "efficient", "max_frames": 50, "strategy": "keyframes", "ocr": False}
    if mode == DetailMode.BALANCED.value:
        return {"mode": "balanced", "max_frames": 100, "strategy": "scene_or_keyframe", "ocr": False}
    if mode == DetailMode.DEEP.value:
        return {"mode": "deep", "max_frames": 180, "strategy": "scene_keyframe_ocr", "ocr": True}
    if mode == DetailMode.FULL.value:
        return {"mode": "full", "max_frames": None, "strategy": "all_scene_changes", "ocr": True}
    raise ValueError(f"unsupported detail mode: {detail}")


def frame_budget(duration_seconds: float, detail: str | DetailMode = DetailMode.BALANCED, *, focused: bool = False) -> int | None:
    mode = normalize_detail_mode(detail)
    defaults = select_detail_defaults(mode, focused=focused)
    cap = defaults["max_frames"]
    if cap is None:
        return None
    cap = int(cap)
    if cap == 0 or duration_seconds <= 0:
        return cap
    if focused:
        if duration_seconds <= 5:
            return min(cap, max(10, round(duration_seconds * 6)))
        if duration_seconds <= 15:
            return min(cap, max(30, round(duration_seconds * 4)))
        if duration_seconds <= 30:
            return min(cap, 60)
        return min(cap, 100)
    if mode == DetailMode.EFFICIENT.value:
        if duration_seconds <= 30:
            return min(cap, max(8, round(duration_seconds * 0.75)))
        return cap
    if mode == DetailMode.DEEP.value:
        if duration_seconds <= 30:
            return min(cap, max(18, round(duration_seconds * 1.5)))
        if duration_seconds <= 60:
            return min(cap, 70)
        if duration_seconds <= 180:
            return min(cap, 110)
        return cap
    # balanced/quick default mirrors Claude Video's duration-budget idea.
    if duration_seconds <= 30:
        return min(cap, max(12, round(duration_seconds)))
    if duration_seconds <= 60:
        return min(cap, 40)
    if duration_seconds <= 180:
        return min(cap, 60)
    if duration_seconds <= 600:
        return min(cap, 80)
    return cap


def cue_frame_timestamps(segments: Iterable[dict], *, pad_seconds: float = 0.0) -> list[float]:
    """Return transcript cue timestamps worth forcing into the visual pass.

    Segments may contain `text` plus `start` or `timestamp_seconds`.
    """
    cues: list[float] = []
    for segment in segments:
        text = str(segment.get("text") or "")
        if not CUE_RE.search(text):
            continue
        value = segment.get("start", segment.get("timestamp_seconds", 0))
        try:
            ts = max(0.0, float(value) + pad_seconds)
        except (TypeError, ValueError):
            continue
        if ts not in cues:
            cues.append(ts)
    return cues
