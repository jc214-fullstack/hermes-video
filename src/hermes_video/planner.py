from __future__ import annotations

import re
from collections.abc import Iterable

from .models import DetailMode

CUE_RE = re.compile(
    r"\b(look here|as you can see|see here|this repo|this repository|this command|install|clone|github|website|tool|watch this)\b",
    re.I,
)


def select_detail_defaults(detail: str | DetailMode, *, focused: bool = False) -> dict[str, object]:
    mode = DetailMode(detail)
    if focused or mode is DetailMode.FOCUSED:
        return {"mode": "focused", "max_frames": 100, "strategy": "dense_range", "ocr": True}
    if mode is DetailMode.QUICK:
        return {"mode": "quick", "max_frames": 0, "strategy": "transcript_first", "ocr": False}
    if mode is DetailMode.BALANCED:
        return {"mode": "balanced", "max_frames": 100, "strategy": "scene_or_keyframe", "ocr": False}
    if mode is DetailMode.DEEP:
        return {"mode": "deep", "max_frames": 180, "strategy": "scene_keyframe_ocr", "ocr": True}
    if mode is DetailMode.FULL:
        return {"mode": "full", "max_frames": None, "strategy": "all_scene_changes", "ocr": True}
    raise ValueError(f"unsupported detail mode: {detail}")


def frame_budget(duration_seconds: float, detail: str | DetailMode = DetailMode.BALANCED, *, focused: bool = False) -> int | None:
    defaults = select_detail_defaults(detail, focused=focused)
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
    mode = DetailMode(detail)
    if mode is DetailMode.DEEP:
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
