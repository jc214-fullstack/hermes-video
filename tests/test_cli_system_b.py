import json
import shutil
import subprocess
from subprocess import DEVNULL

import pytest

from hermes_video.cli import main


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe unavailable",
)
def test_watch_json_emits_stable_system_b_summary(tmp_path, capsys):
    video = tmp_path / "v.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=4:size=160x90:rate=5",
         "-pix_fmt", "yuv420p", str(video)],
        check=True, stdout=DEVNULL, stderr=DEVNULL,
    )
    workspace = tmp_path / "ws"

    result = main([
        "watch", str(video), "--platform", "direct", "--media-path", str(video),
        "--detail", "balanced", "--workspace", str(workspace),
        "--timestamps", "1.0,2.5", "--json",
    ])

    assert result == 0
    data = json.loads(capsys.readouterr().out)
    # Backward-compatible keys preserved.
    assert data["workspace"] == str(workspace)
    assert data["paths"]["manifest"].endswith("manifest.json")
    summary = data["summary"]
    for key in ("evidence_status", "transcript", "frames", "ocr", "media", "warnings", "manifest_path"):
        assert key in summary
    assert summary["frames"]["count"] >= 1
    assert isinstance(summary["frames"]["paths"], list)
    assert summary["transcript"]["status"] in {"captions", "stt", "unavailable", "missing"}

    manifest = json.loads((workspace / "manifest.json").read_text())
    user_frames = [f for f in manifest["frame_candidates"] if f["reason"] == "user_timestamp"]
    assert len(user_frames) == 2
