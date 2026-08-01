import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hermes_video import VideoEvidenceRequest, write_workspace_bundle
from hermes_video.media_extract import (
    active_dedup_backend,
    deduplicate_frame_candidates,
    perceptual_dedup_available,
)
from hermes_video.models import FrameCandidate


def test_quick_url_uses_metadata_and_captions_without_media_download(tmp_path, monkeypatch):
    captions_path = tmp_path / "downloaded" / "video.en.vtt"

    def fake_fetch_metadata(url):
        return {
            "blocked": False,
            "title": "Demo URL",
            "duration_seconds": 9.0,
            "webpage_url": url,
            "subtitle_langs": ["en"],
            "auto_caption_langs": [],
        }

    def fake_pick_caption_lang(meta):
        return "en"

    def fake_download_captions(url, out_dir, *, lang="en", auto=True):
        captions_path.parent.mkdir(parents=True, exist_ok=True)
        captions_path.write_text(
            "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello from captions\n",
            encoding="utf-8",
        )
        return captions_path

    def fail_download_media(*args, **kwargs):  # pragma: no cover - assertion helper
        raise AssertionError("quick caption-only URL pass must not download media")

    monkeypatch.setattr("hermes_video.bundle.fetch_metadata", fake_fetch_metadata)
    monkeypatch.setattr("hermes_video.bundle.pick_caption_lang", fake_pick_caption_lang)
    monkeypatch.setattr("hermes_video.bundle.download_captions", fake_download_captions)
    monkeypatch.setattr("hermes_video.bundle.download_media", fail_download_media)

    workspace = tmp_path / "bundle"
    write_workspace_bundle(VideoEvidenceRequest(source_url="https://example.test/video", platform="youtube", detail="quick"), workspace)

    manifest = json.loads((workspace / "manifest.json").read_text())
    metadata = json.loads((workspace / "video" / "metadata.json").read_text())
    transcript = (workspace / "video" / "transcript.md").read_text()

    assert manifest["media"] == "skipped"
    assert manifest["transcript"] == "captions"
    assert manifest["transcript_source"] == "captions"
    assert manifest["frames"] == "skipped"
    assert manifest["evidence_status"] == "partial_extraction"
    assert metadata["url_metadata"]["title"] == "Demo URL"
    assert "hello from captions" in transcript


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="ffmpeg/ffprobe unavailable")
def test_balanced_url_downloads_media_for_visual_evidence(tmp_path, monkeypatch):
    video = tmp_path / "fixture.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=160x90:rate=5", "-pix_fmt", "yuv420p", str(video)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    monkeypatch.setattr(
        "hermes_video.bundle.fetch_metadata",
        lambda url: {"blocked": False, "title": "Download me", "duration_seconds": 3.0, "subtitle_langs": [], "auto_caption_langs": []},
    )
    monkeypatch.setattr("hermes_video.bundle.pick_caption_lang", lambda meta: None)
    monkeypatch.setattr("hermes_video.bundle.download_media", lambda url, out_dir: video)

    workspace = tmp_path / "bundle"
    write_workspace_bundle(VideoEvidenceRequest(source_url="https://example.test/video", platform="youtube", detail="balanced"), workspace)

    manifest = json.loads((workspace / "manifest.json").read_text())
    assert manifest["media"] == "downloaded"
    assert manifest["frames"] == "extracted"
    assert manifest["evidence_status"] == "partial_extraction"
    assert manifest["metadata"]["downloaded_media_path"] == str(video)
    assert manifest["metadata"]["frames_selected"] > 0


def test_deduplicate_frame_candidates_drops_exact_duplicate_files(tmp_path):
    one = tmp_path / "one.jpg"
    two = tmp_path / "two.jpg"
    three = tmp_path / "three.jpg"
    one.write_bytes(b"same-image-bytes")
    two.write_bytes(b"same-image-bytes")
    three.write_bytes(b"different-image-bytes")

    kept, dropped = deduplicate_frame_candidates([
        FrameCandidate(index=1, timestamp_seconds=0.0, reason="uniform", path=str(one)),
        FrameCandidate(index=2, timestamp_seconds=1.0, reason="uniform", path=str(two)),
        FrameCandidate(index=3, timestamp_seconds=2.0, reason="transcript_cue", path=str(three), cue_text="look here"),
    ])

    assert [Path(frame.path).name for frame in kept] == ["one.jpg", "three.jpg"]
    assert dropped == 1


def _write_jpeg(path, image, quality):
    image.save(path, format="JPEG", quality=quality)


def test_perceptual_dedup_drops_near_duplicate_reencoded_frames(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    assert perceptual_dedup_available()
    assert active_dedup_backend() == "perceptual"

    base = Image.new("RGB", (64, 64))
    base.putdata([((x * 4) % 256, (y * 4) % 256, 0) for y in range(64) for x in range(64)])
    other = Image.new("RGB", (64, 64), color=(10, 200, 30))

    high = tmp_path / "high.jpg"
    low = tmp_path / "low.jpg"
    different = tmp_path / "different.jpg"
    _write_jpeg(high, base, 95)
    _write_jpeg(low, base, 20)
    _write_jpeg(different, other, 95)

    # Re-encoding at a different quality changes bytes but not the visual frame.
    assert high.read_bytes() != low.read_bytes()

    kept, dropped = deduplicate_frame_candidates([
        FrameCandidate(index=1, timestamp_seconds=0.0, reason="uniform", path=str(high)),
        FrameCandidate(index=2, timestamp_seconds=1.0, reason="uniform", path=str(low)),
        FrameCandidate(index=3, timestamp_seconds=2.0, reason="scene", path=str(different)),
    ])

    assert [Path(frame.path).name for frame in kept] == ["high.jpg", "different.jpg"]
    assert dropped == 1


def test_perceptual_dedup_preserves_forced_frames(tmp_path):
    Image = pytest.importorskip("PIL.Image")

    frame = Image.new("RGB", (64, 64), color=(120, 120, 120))
    a = tmp_path / "cue_a.jpg"
    b = tmp_path / "cue_b.jpg"
    _write_jpeg(a, frame, 95)
    _write_jpeg(b, frame, 30)

    # Two explicitly requested moments that happen to look near-identical must
    # both survive; forced frames are exempt from perceptual suppression.
    kept, dropped = deduplicate_frame_candidates([
        FrameCandidate(index=1, timestamp_seconds=1.0, reason="user_timestamp", path=str(a)),
        FrameCandidate(index=2, timestamp_seconds=2.5, reason="transcript_cue", path=str(b), cue_text="look here"),
    ])

    assert [Path(f.path).name for f in kept] == ["cue_a.jpg", "cue_b.jpg"]
    assert dropped == 0
