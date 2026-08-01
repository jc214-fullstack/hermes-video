import shutil
import subprocess
from subprocess import DEVNULL

import pytest

from hermes_video.media_extract import extract_frames_at_timestamps, extract_mode_frames

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe unavailable",
)


def _make_video(path, *, duration=4, size="160x90"):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=duration={duration}:size={size}:rate=5",
         "-pix_fmt", "yuv420p", str(path)],
        check=True, stdout=DEVNULL, stderr=DEVNULL,
    )
    return path


def test_focused_range_constrains_frames_and_records_reason(tmp_path):
    video = _make_video(tmp_path / "v.mp4", duration=6)
    frames = extract_mode_frames(
        video, tmp_path / "frames", duration_seconds=6, detail="balanced", start=2.0, end=4.0
    )
    assert frames
    assert {f.reason for f in frames} == {"focused_range"}
    assert all(1.5 <= f.timestamp_seconds <= 4.5 for f in frames)


def test_sampled_frames_record_scene_or_uniform_reason(tmp_path):
    video = _make_video(tmp_path / "v.mp4", duration=4)
    frames = extract_mode_frames(video, tmp_path / "frames", duration_seconds=4, detail="balanced")
    assert frames
    assert {f.reason for f in frames} <= {"scene", "uniform"}


def test_efficient_mode_prefers_keyframe_or_uniform(tmp_path):
    video = _make_video(tmp_path / "v.mp4", duration=4)
    frames = extract_mode_frames(video, tmp_path / "frames", duration_seconds=4, detail="efficient")
    assert frames
    assert {f.reason for f in frames} <= {"keyframe", "uniform"}


def test_user_timestamp_frames_carry_reason(tmp_path):
    video = _make_video(tmp_path / "v.mp4", duration=6)
    frames = extract_frames_at_timestamps(
        video, tmp_path / "frames", [{"timestamp_seconds": 3.0}], reason="user_timestamp"
    )
    assert frames and frames[0].reason == "user_timestamp"
    assert abs(frames[0].timestamp_seconds - 3.0) < 0.01
