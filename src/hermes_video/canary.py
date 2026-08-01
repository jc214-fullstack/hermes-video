"""Deterministic offline canaries for the Hermes Video evidence engine.

Each canary builds a local fixture (no network), runs the real bundle path, and
asserts the evidence contract. The live-URL canary is gated: without an explicit
URL it reports ``skipped_live_url`` instead of fabricating a network success.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from . import bundle as bundle_module
from .bundle import write_workspace_bundle
from .media_extract import deduplicate_frame_candidates, extract_uniform_frames
from .models import VideoEvidenceRequest
from .ocr import ocr_available

_DEVNULL = subprocess.DEVNULL


def _testsrc(path: Path, *, duration: int = 4, size: str = "160x90") -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=duration={duration}:size={size}:rate=5",
         "-pix_fmt", "yuv420p", str(path)],
        check=True, stdout=_DEVNULL, stderr=_DEVNULL,
    )
    return path


def _static_video(path: Path, *, duration: int = 4) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=blue:size=160x90:duration={duration}:rate=5",
         "-pix_fmt", "yuv420p", str(path)],
        check=True, stdout=_DEVNULL, stderr=_DEVNULL,
    )
    return path


def _text_video(path: Path, text: str, *, duration: int = 3) -> Path:
    """Render a PNG with PIL, then loop it into an mp4 (no font-path guesswork)."""
    from PIL import Image, ImageDraw

    png = path.with_suffix(".png")
    img = Image.new("RGB", (320, 120), (255, 255, 255))
    ImageDraw.Draw(img).text((10, 45), text, fill=(0, 0, 0))
    img.save(png)
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-t", str(duration),
         "-vf", "fps=5", "-pix_fmt", "yuv420p", str(path)],
        check=True, stdout=_DEVNULL, stderr=_DEVNULL,
    )
    return path


def _passed(detail: str, **extra) -> dict:
    return {"status": "passed", "detail": detail, **extra}


def _c_synthetic_local_video(root: Path) -> dict:
    video = _testsrc(root / "synthetic.mp4")
    ws = root / "synthetic_ws"
    write_workspace_bundle(
        VideoEvidenceRequest(source_url=str(video), platform="direct", media_path=str(video), detail="balanced"),
        ws,
    )
    manifest = json.loads((ws / "manifest.json").read_text())
    assert manifest["media"] == "provided", manifest["media"]
    assert manifest["frames"] == "extracted", manifest["frames"]
    assert manifest["evidence_status"] in {"partial_extraction", "full"}, manifest["evidence_status"]
    return _passed(f"frames={manifest['metadata']['frames_selected']} status={manifest['evidence_status']}")


def _c_ocr_text_video(root: Path) -> dict:
    if not ocr_available():
        return {"status": "skipped", "detail": "tesseract unavailable"}
    video = _text_video(root / "textcard.mp4", "HELLO REPO GITHUB")
    ws = root / "ocr_ws"
    write_workspace_bundle(
        VideoEvidenceRequest(source_url=str(video), platform="direct", media_path=str(video), detail="deep"),
        ws,
    )
    manifest = json.loads((ws / "manifest.json").read_text())
    assert manifest["ocr"] in {"extracted", "empty"}, manifest["ocr"]
    ocr_text = (ws / "video" / "ocr.md").read_text().upper() if (ws / "video" / "ocr.md").exists() else ""
    assert "REPO" in ocr_text, f"ocr text missing REPO: {ocr_text[:120]!r}"
    return _passed(f"ocr={manifest['ocr']}")


def _c_caption_cue_frame(root: Path) -> dict:
    video = _testsrc(root / "cue.mp4", duration=6)
    caps = root / "cue.vtt"
    caps.write_text(
        "WEBVTT\n\n00:00:00.500 --> 00:00:02.000\nintro\n\n"
        "00:00:03.000 --> 00:00:05.000\nlook at this repo on github\n",
        encoding="utf-8",
    )
    ws = root / "cue_ws"
    write_workspace_bundle(
        VideoEvidenceRequest(source_url=str(video), platform="direct", media_path=str(video),
                             detail="balanced", captions_path=str(caps)),
        ws,
    )
    manifest = json.loads((ws / "manifest.json").read_text())
    cue_frames = [f for f in manifest["frame_candidates"] if f["reason"] == "transcript_cue"]
    assert manifest["transcript"] == "captions", manifest["transcript"]
    assert cue_frames, "expected a transcript_cue frame"
    return _passed(f"cue_frames={len(cue_frames)}")


def _c_focused_range(root: Path) -> dict:
    video = _testsrc(root / "focused.mp4", duration=6)
    ws = root / "focused_ws"
    write_workspace_bundle(
        VideoEvidenceRequest(source_url=str(video), platform="direct", media_path=str(video),
                             detail="focused", start=2.0, end=4.0, timestamps=(1.0,)),
        ws,
    )
    manifest = json.loads((ws / "manifest.json").read_text())
    reasons = {f["reason"] for f in manifest["frame_candidates"]}
    assert "focused_range" in reasons, reasons
    assert "user_timestamp" in reasons, reasons
    assert manifest["metadata"]["focused_start"] == 2.0
    return _passed(f"reasons={sorted(reasons)}")


def _c_duplicate_frames(root: Path) -> dict:
    video = _static_video(root / "static.mp4")
    frames = extract_uniform_frames(video, root / "static_frames", duration_seconds=4, budget=12, reason="uniform")
    kept, dropped = deduplicate_frame_candidates(frames)
    assert dropped > 0, f"static video should yield duplicate frames, dropped={dropped}"
    assert len(kept) < len(frames), (len(kept), len(frames))
    return _passed(f"candidate={len(frames)} kept={len(kept)} dropped={dropped}")


def _c_blocked_url(root: Path) -> dict:
    original = bundle_module.fetch_metadata
    bundle_module.fetch_metadata = lambda url: {"blocked": True, "error": "canary mock blocker"}
    try:
        ws = root / "blocked_ws"
        write_workspace_bundle(
            VideoEvidenceRequest(source_url="https://blocked.test/video", platform="youtube", detail="balanced"),
            ws,
        )
        manifest = json.loads((ws / "manifest.json").read_text())
    finally:
        bundle_module.fetch_metadata = original
    assert manifest["evidence_status"] == "blocked", manifest["evidence_status"]
    assert any("blocked" in w for w in manifest["warnings"]), manifest["warnings"]
    return _passed("evidence_status=blocked")


def _c_live_url(root: Path, live_url: str | None) -> dict:
    if not live_url:
        return {"status": "skipped_live_url", "detail": "no --live-url supplied; live network canary not run"}
    ws = root / "live_ws"
    try:
        write_workspace_bundle(
            VideoEvidenceRequest(source_url=live_url, platform="unknown", detail="quick"),
            ws,
        )
        manifest = json.loads((ws / "manifest.json").read_text())
    except Exception as exc:  # honest partial/blocker, never a fabricated pass
        return {"status": "failed", "detail": f"live url raised {type(exc).__name__}: {exc}"}
    status = manifest["evidence_status"]
    if status == "blocked":
        return {"status": "failed", "detail": f"live url blocked: {manifest['warnings']}"}
    return _passed(f"live evidence_status={status}", evidence_status=status)


_OFFLINE = [
    ("synthetic_local_video", _c_synthetic_local_video),
    ("ocr_text_video", _c_ocr_text_video),
    ("caption_cue_frame", _c_caption_cue_frame),
    ("focused_range", _c_focused_range),
    ("duplicate_frames", _c_duplicate_frames),
    ("blocked_url", _c_blocked_url),
]


def run_canaries(*, live_url: str | None = None, workdir: str | Path | None = None) -> dict:
    """Run all canaries and return a report dict. Offline canaries never touch the network."""
    tmp = None
    if workdir is None:
        tmp = tempfile.TemporaryDirectory(prefix="hermes-video-canary-")
        root = Path(tmp.name)
    else:
        root = Path(workdir)
        root.mkdir(parents=True, exist_ok=True)
    canaries: list[dict] = []
    try:
        for name, fn in _OFFLINE:
            case_root = root / name
            case_root.mkdir(parents=True, exist_ok=True)
            try:
                result = fn(case_root)
            except Exception as exc:
                result = {"status": "failed", "detail": f"{type(exc).__name__}: {exc}"}
            canaries.append({"name": name, **result})
        canaries.append({"name": "live_url", **_c_live_url(root / "live_url", live_url)})
    finally:
        if tmp is not None:
            tmp.cleanup()
    failed = [c for c in canaries if c["status"] == "failed"]
    return {
        "status": "ok" if not failed else "failed",
        "passed": sum(1 for c in canaries if c["status"] == "passed"),
        "failed": len(failed),
        "skipped": sum(1 for c in canaries if c["status"].startswith("skipped")),
        "canaries": canaries,
    }


def write_report(report: dict, out_path: str | Path) -> dict[str, str]:
    """Write ``<out_path>.json`` and ``<out_path>.md``; return the two paths."""
    base = Path(out_path)
    base.parent.mkdir(parents=True, exist_ok=True)
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Hermes Video canary report",
        "",
        f"Status: **{report['status']}** — passed {report['passed']}, failed {report['failed']}, skipped {report['skipped']}",
        "",
        "| Canary | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for c in report["canaries"]:
        lines.append(f"| {c['name']} | {c['status']} | {c.get('detail', '')} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
