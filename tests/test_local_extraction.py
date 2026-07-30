import json
import shutil
import subprocess

import pytest

from hermes_video import VideoEvidenceRequest, write_workspace_bundle


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="ffmpeg/ffprobe unavailable")
def test_write_workspace_bundle_extracts_local_video_frames_audio_and_analysis_ready(tmp_path):
    video = tmp_path / "fixture.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=320x180:rate=5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=2",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    workspace = tmp_path / "bundle"
    paths = write_workspace_bundle(
        VideoEvidenceRequest(source_url=str(video), platform="direct", media_path=str(video), detail="balanced", prompt="summarize"),
        workspace,
    )

    manifest = json.loads((workspace / "manifest.json").read_text())
    assert manifest["media"] == "provided"
    assert manifest["frames"] == "extracted"
    assert manifest["transcript"] in {"missing", "unavailable"}
    assert manifest["metadata"]["probe"]["duration_seconds"] > 0
    assert list((workspace / "video" / "frames").glob("*.jpg"))
    assert (workspace / "video" / "audio.wav").exists()
    assert (workspace / "analysis-ready.md").exists()
    assert "Timestamped frames" in (workspace / "analysis-ready.md").read_text()
    assert "analysis_ready" in paths
