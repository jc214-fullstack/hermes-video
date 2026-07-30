from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .models import FrameCandidate
from .planner import frame_budget


def _run_json(argv: list[str]) -> dict:
    proc = subprocess.run(argv, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout or "{}")


def ffprobe_media(media_path: str | Path) -> dict[str, object]:
    raw = _run_json([
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(media_path),
    ])
    fmt = raw.get("format", {})
    streams = raw.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    duration = fmt.get("duration") or video_stream.get("duration") or 0
    try:
        duration_seconds = float(duration)
    except (TypeError, ValueError):
        duration_seconds = 0.0
    return {
        "duration_seconds": duration_seconds,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "has_audio": bool(audio_stream),
    }


def extract_audio(media_path: str | Path, output_path: str | Path) -> Path | None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", str(media_path), "-vn", "-ac", "1", "-ar", "16000", str(output)],
        capture_output=True,
        text=True,
    )
    return output if proc.returncode == 0 and output.exists() else None


def extract_frames(media_path: str | Path, frames_dir: str | Path, *, duration_seconds: float, detail: str) -> list[FrameCandidate]:
    frames_root = Path(frames_dir)
    frames_root.mkdir(parents=True, exist_ok=True)
    budget = frame_budget(duration_seconds or 0, detail) or 0
    budget = max(1, min(int(budget), 12))  # v1 local extraction cap; planner still records full budget.
    fps = budget / duration_seconds if duration_seconds else 1
    fps = max(0.2, min(fps, 2.0))
    pattern = frames_root / "frame-%04d.jpg"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(media_path), "-vf", f"fps={fps}", "-q:v", "2", str(pattern)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    paths = sorted(frames_root.glob("frame-*.jpg"))[:budget]
    interval = duration_seconds / max(len(paths), 1) if duration_seconds else 0
    return [
        FrameCandidate(index=i + 1, timestamp_seconds=round(i * interval, 3), reason="uniform", path=str(path))
        for i, path in enumerate(paths)
    ]
