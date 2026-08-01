from __future__ import annotations

import json
import hashlib
import re
import subprocess
from pathlib import Path

from .models import FrameCandidate
from .planner import frame_budget, normalize_detail_mode, select_detail_defaults

_FRAME_CAP = 12  # v1 local extraction cap; planner still records the full budget.
_PTS_RE = re.compile(r"pts_time:([0-9.]+)")

PERCEPTUAL_HAMMING_THRESHOLD = 4  # aHash bit-distance below which frames are near-duplicates
_FORCED_FRAME_REASONS = {"user_timestamp", "transcript_cue"}  # explicit intent; never perceptually dropped

try:  # optional: Pillow enables perceptual near-duplicate dedup
    from PIL import Image  # type: ignore
    _PIL_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only without Pillow installed
    Image = None  # type: ignore
    _PIL_AVAILABLE = False


def perceptual_dedup_available() -> bool:
    return _PIL_AVAILABLE


def active_dedup_backend() -> str:
    return "perceptual" if _PIL_AVAILABLE else "exact"


def _average_hash(path: Path) -> int | None:
    """64-bit deterministic average hash, or None when Pillow can't read the file."""
    if not _PIL_AVAILABLE:
        return None
    try:
        with Image.open(path) as img:
            pixels = img.convert("L").resize((8, 8)).tobytes()
    except Exception:
        return None
    avg = sum(pixels) / len(pixels)
    bits = 0
    for i, px in enumerate(pixels):
        if px >= avg:
            bits |= 1 << i
    return bits


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


def _resolve_budget(duration_seconds: float, detail: str, *, focused: bool) -> int:
    """Return the capped local frame count, or 0 when the mode wants no frames."""
    raw = frame_budget(duration_seconds or 0, detail, focused=focused)
    if raw == 0:
        return 0
    cap = _FRAME_CAP if raw is None else min(int(raw), _FRAME_CAP)
    return max(1, cap)


def extract_uniform_frames(
    media_path: str | Path,
    frames_dir: str | Path,
    *,
    duration_seconds: float,
    budget: int,
    start: float | None = None,
    end: float | None = None,
    reason: str = "uniform",
) -> list[FrameCandidate]:
    """Deterministic time-uniform sampling, optionally constrained to a window."""
    frames_root = Path(frames_dir)
    frames_root.mkdir(parents=True, exist_ok=True)
    window_start = float(start) if start is not None else 0.0
    window_end = float(end) if end is not None else float(duration_seconds or 0)
    span = window_end - window_start
    if span <= 0:
        span = float(duration_seconds or 0) or 1.0
    fps = budget / span if span else 1
    fps = max(0.2, min(fps, 5.0))
    pattern = frames_root / f"{reason}-%04d.jpg"
    argv = ["ffmpeg", "-y"]
    if start is not None:
        argv += ["-ss", str(window_start)]
    argv += ["-i", str(media_path)]
    if end is not None:
        argv += ["-t", str(max(window_end - window_start, 0.001))]
    argv += ["-vf", f"fps={fps}", "-q:v", "2", str(pattern)]
    subprocess.run(argv, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    paths = sorted(frames_root.glob(f"{reason}-*.jpg"))[:budget]
    interval = span / max(len(paths), 1)
    return [
        FrameCandidate(index=i + 1, timestamp_seconds=round(window_start + i * interval, 3), reason=reason, path=str(path))
        for i, path in enumerate(paths)
    ]


def _extract_selected_frames(
    media_path: str | Path,
    frames_dir: str | Path,
    *,
    select_expr: str,
    prefix: str,
    reason: str,
    budget: int,
) -> list[FrameCandidate]:
    """Run an ffmpeg ``select`` filter with showinfo, recovering real timestamps."""
    frames_root = Path(frames_dir)
    frames_root.mkdir(parents=True, exist_ok=True)
    pattern = frames_root / f"{prefix}-%04d.jpg"
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", str(media_path), "-vf", f"{select_expr},showinfo",
         "-vsync", "vfr", "-q:v", "2", str(pattern)],
        capture_output=True, text=True,
    )
    times = [float(t) for t in _PTS_RE.findall(proc.stderr or "")]
    paths = sorted(frames_root.glob(f"{prefix}-*.jpg"))[:budget]
    out: list[FrameCandidate] = []
    for i, path in enumerate(paths):
        ts = times[i] if i < len(times) else 0.0
        out.append(FrameCandidate(index=i + 1, timestamp_seconds=round(ts, 3), reason=reason, path=str(path)))
    return out


def extract_scene_frames(media_path, frames_dir, *, budget: int, threshold: float = 0.3) -> list[FrameCandidate]:
    return _extract_selected_frames(
        media_path, frames_dir,
        select_expr=f"select='gt(scene,{threshold})'", prefix="scene", reason="scene", budget=budget,
    )


def extract_keyframes(media_path, frames_dir, *, budget: int) -> list[FrameCandidate]:
    return _extract_selected_frames(
        media_path, frames_dir,
        select_expr="select='eq(pict_type,I)'", prefix="keyframe", reason="keyframe", budget=budget,
    )


def extract_mode_frames(
    media_path: str | Path,
    frames_dir: str | Path,
    *,
    duration_seconds: float,
    detail: str,
    start: float | None = None,
    end: float | None = None,
) -> list[FrameCandidate]:
    """Select sampled frames by detail mode with a deterministic uniform fallback.

    Focused ranges (``start``/``end`` or focused mode) win and are sampled
    densely inside the window as ``focused_range``. Otherwise scene/keyframe
    extraction is attempted per strategy, falling back to uniform sampling when
    the detector returns nothing.
    """
    detail = normalize_detail_mode(detail)
    focused = detail == "focused" or start is not None or end is not None
    budget = _resolve_budget(duration_seconds, detail, focused=focused)
    if budget == 0:
        return []
    if focused:
        return extract_uniform_frames(
            media_path, frames_dir, duration_seconds=duration_seconds, budget=budget,
            start=start, end=end, reason="focused_range",
        )
    strategy = str(select_detail_defaults(detail)["strategy"])
    if strategy == "keyframes":
        frames = extract_keyframes(media_path, frames_dir, budget=budget)
        if frames:
            return frames
    elif strategy in {"scene_or_keyframe", "scene_keyframe_ocr", "all_scene_changes"}:
        frames = extract_scene_frames(media_path, frames_dir, budget=budget)
        if frames:
            return frames
    return extract_uniform_frames(
        media_path, frames_dir, duration_seconds=duration_seconds, budget=budget, reason="uniform",
    )


def extract_frames_at_timestamps(
    media_path: str | Path,
    frames_dir: str | Path,
    cues: list[dict],
    *,
    reason: str = "transcript_cue",
) -> list[FrameCandidate]:
    """Extract one frame per cue timestamp (accurate seek).

    ``cues`` is ``[{timestamp_seconds, cue_text}]``. Frames are named
    ``cue-<ts>.jpg`` so they never collide with uniform ``frame-*.jpg`` output.
    """
    frames_root = Path(frames_dir)
    frames_root.mkdir(parents=True, exist_ok=True)
    out: list[FrameCandidate] = []
    for i, cue in enumerate(cues):
        ts = float(cue.get("timestamp_seconds", 0) or 0)
        target = frames_root / f"cue-{ts:08.3f}.jpg"
        proc = subprocess.run(
            ["ffmpeg", "-y", "-ss", str(ts), "-i", str(media_path), "-frames:v", "1", "-q:v", "2", str(target)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode == 0 and target.exists():
            out.append(
                FrameCandidate(
                    index=i + 1,
                    timestamp_seconds=round(ts, 3),
                    reason=reason,
                    path=str(target),
                    cue_text=cue.get("cue_text"),
                )
            )
    return out


def deduplicate_frame_candidates(
    candidates: list[FrameCandidate],
    *,
    threshold: int = PERCEPTUAL_HAMMING_THRESHOLD,
) -> tuple[list[FrameCandidate], int]:
    """Drop duplicate frame files while preserving order.

    With Pillow present this is a perceptual pass: an 8x8 average hash catches
    near-duplicate frames whose bytes differ (re-encoded static screens) but
    whose picture is identical, within ``threshold`` Hamming bits. Without
    Pillow it degrades to exact sha256 byte hashing. Both are deterministic.

    Input order matters: forced frames (user timestamps, transcript cues) lead
    the list, so a kept frame always wins over a later sampled duplicate.
    Forced frames are explicit intent, so they are exempt from perceptual
    suppression (only an exact byte duplicate ever drops one); perceptual
    near-duplicate dropping applies to sampled frames.
    """
    exact_seen: set[str] = set()
    kept_hashes: list[int] = []  # ponytail: O(n*kept) scan; frames per bundle <= ~30
    kept: list[FrameCandidate] = []
    dropped = 0
    for candidate in candidates:
        if not candidate.path:
            kept.append(candidate)
            continue
        path = Path(candidate.path)
        if not path.exists():
            kept.append(candidate)
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in exact_seen:
            dropped += 1
            continue
        phash = _average_hash(path)
        forced = candidate.reason in _FORCED_FRAME_REASONS
        if not forced and phash is not None and any((phash ^ seen).bit_count() <= threshold for seen in kept_hashes):
            dropped += 1
            continue
        exact_seen.add(digest)
        if phash is not None:
            kept_hashes.append(phash)
        kept.append(candidate)
    return kept, dropped
