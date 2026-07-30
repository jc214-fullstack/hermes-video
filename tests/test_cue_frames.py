import json
import shutil
import subprocess

import pytest

from hermes_video import VideoEvidenceRequest, cue_frame_segments, write_workspace_bundle


def test_cue_frame_segments_pair_timestamp_and_text():
    segments = [
        {"start": 1.0, "text": "intro"},
        {"start": 7.5, "text": "as you can see this repo has the command"},
    ]
    cues = cue_frame_segments(segments)
    assert cues == [{"timestamp_seconds": 7.5, "cue_text": "as you can see this repo has the command", "cue_phrase": "as you can see"}]


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="ffmpeg/ffprobe unavailable")
def test_bundle_forces_cue_frames_from_captions(tmp_path):
    video = tmp_path / "fixture.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=6:size=320x180:rate=5",
         "-pix_fmt", "yuv420p", str(video)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    captions = tmp_path / "caps.vtt"
    captions.write_text(
        "WEBVTT\n\n00:00:00.500 --> 00:00:02.000\nintro\n\n"
        "00:00:03.000 --> 00:00:05.000\nlook at this repo on github\n",
        encoding="utf-8",
    )

    workspace = tmp_path / "bundle"
    write_workspace_bundle(
        VideoEvidenceRequest(source_url=str(video), platform="direct", media_path=str(video),
                             detail="balanced", captions_path=str(captions)),
        workspace,
    )

    manifest = json.loads((workspace / "manifest.json").read_text())
    assert manifest["transcript"] == "captions"
    assert manifest["transcript_source"] == "captions"
    cue_frames = [f for f in manifest["frame_candidates"] if f["reason"] == "transcript_cue"]
    assert cue_frames, "expected a transcript-cue frame"
    assert cue_frames[0]["cue_text"] == "look at this repo on github"
    assert abs(cue_frames[0]["timestamp_seconds"] - 3.0) < 0.01
    analysis = (workspace / "analysis-ready.md").read_text()
    assert "cue:" in analysis
