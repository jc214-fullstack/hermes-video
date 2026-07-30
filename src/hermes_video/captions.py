"""Native caption/subtitle parsing (VTT/SRT) into transcript segments."""
from __future__ import annotations

import re
from pathlib import Path

# HH:MM:SS.mmm (VTT) or HH:MM:SS,mmm (SRT); hours optional.
_TS = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{1,3})")
_CUE_LINE = re.compile(r"(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3}|\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*(\S+)")
_TAG = re.compile(r"<[^>]+>")


def _to_seconds(stamp: str) -> float | None:
    m = _TS.search(stamp)
    if not m:
        return None
    hours = int(m.group(1) or 0)
    return hours * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4).ljust(3, "0")) / 1000


def parse_captions(text: str) -> list[dict]:
    """Parse VTT or SRT text into ``[{start, end, text}]`` segments.

    Handles both formats, strips inline tags, and drops empty/duplicate cues
    (YouTube auto-captions repeat rolling lines).
    """
    segments: list[dict] = []
    block: list[str] = []
    last_text = None

    def flush() -> None:
        nonlocal last_text
        if not block:
            return
        header = next((line for line in block if "-->" in line), None)
        if header:
            cue = _CUE_LINE.search(header)
            if cue:
                start = _to_seconds(cue.group(1))
                end = _to_seconds(cue.group(2))
                body_lines = block[block.index(header) + 1 :]
                body = _TAG.sub("", " ".join(body_lines)).strip()
                if start is not None and body and body != last_text:
                    segments.append({"start": start, "end": end, "text": body})
                    last_text = body
        block.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line == "WEBVTT" or line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        if line.isdigit() and not block:  # SRT sequence index
            continue
        block.append(line)
    flush()
    return segments


def load_captions(path: str | Path) -> list[dict]:
    return parse_captions(Path(path).read_text(encoding="utf-8", errors="replace"))


def segments_to_markdown(segments: list[dict], *, source: str) -> str:
    lines = [f"# Transcript\n", f"Source: {source}\n", f"Segments: {len(segments)}\n"]
    for seg in segments:
        start = float(seg.get("start", 0) or 0)
        stamp = f"{int(start // 60):02d}:{start % 60:06.3f}"
        lines.append(f"- [{stamp}] {str(seg.get('text') or '').strip()}")
    return "\n".join(lines) + "\n"
