from __future__ import annotations

import json
from pathlib import Path

from .media_extract import extract_audio, extract_frames, ffprobe_media
from .models import VideoEvidenceManifest, VideoEvidenceRequest
from .planner import frame_budget, normalize_detail_mode, select_detail_defaults


def build_planned_manifest(request: VideoEvidenceRequest, *, duration_seconds: float | None = None) -> VideoEvidenceManifest:
    detail = normalize_detail_mode(request.detail)
    focused = detail == "focused" or request.start is not None or request.end is not None
    budget = frame_budget(duration_seconds or 0, detail, focused=focused)
    defaults = select_detail_defaults(detail, focused=focused)
    media_status = "provided" if request.media_path else "missing"
    warnings: list[str] = []
    if duration_seconds is None:
        warnings.append("duration_unknown: frame budget is provisional")
    if not request.media_path and request.platform not in {"youtube", "direct"}:
        warnings.append("media_path_missing: platform resolver must recover video before visual pass")
    return VideoEvidenceManifest(
        source_url=request.source_url,
        platform=request.platform,
        detail=detail,
        media=media_status,
        evidence_status="metadata_only" if media_status == "missing" else "partial_extraction",
        warnings=warnings,
        metadata={
            "duration_seconds": duration_seconds,
            "planning_defaults": defaults,
            "planned_frame_budget": budget,
            "workspace": request.workspace,
        },
    )


def _write_analysis_ready(root: Path, manifest: VideoEvidenceManifest) -> Path:
    target = root / "analysis-ready.md"
    frame_lines = []
    for frame in manifest.frame_candidates:
        frame_lines.append(f"- {frame.timestamp_seconds:.3f}s — `{Path(frame.path or '').as_posix()}` — reason: {frame.reason}")
    target.write_text(
        "# Hermes Video analysis-ready bundle\n\n"
        f"Source: {manifest.source_url}\n"
        f"Platform: {manifest.platform}\n"
        f"Detail: {manifest.detail}\n"
        f"Evidence status: {manifest.evidence_status}\n"
        f"Transcript status: {manifest.transcript}\n"
        f"Frame status: {manifest.frames}\n\n"
        "## Timestamped frames\n\n"
        + ("\n".join(frame_lines) if frame_lines else "No frames extracted.")
        + "\n\n## Warnings\n\n"
        + ("\n".join(f"- {warning}" for warning in manifest.warnings) if manifest.warnings else "None")
        + "\n",
        encoding="utf-8",
    )
    return target


def write_workspace_bundle(request: VideoEvidenceRequest, workspace: str | Path, *, duration_seconds: float | None = None) -> dict[str, str]:
    """Write the Hermes Video workspace contract.

    If a real local `media_path` exists, v1 extracts ffprobe metadata, sampled
    frames, and mono 16 kHz audio. Otherwise it writes an honest planned bundle.
    """
    root = Path(workspace)
    video_dir = root / "video"
    frames_dir = video_dir / "frames"
    video_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(exist_ok=True)

    manifest = build_planned_manifest(request, duration_seconds=duration_seconds)
    media_path = Path(request.media_path) if request.media_path else None
    if media_path and media_path.exists():
        probe = ffprobe_media(media_path)
        actual_duration = float(probe.get("duration_seconds") or duration_seconds or 0)
        manifest.metadata["probe"] = probe
        manifest.metadata["duration_seconds"] = actual_duration
        audio_path = extract_audio(media_path, video_dir / "audio.wav")
        manifest.metadata["audio_path"] = str(audio_path) if audio_path else None
        if audio_path:
            manifest.transcript = "unavailable"
            manifest.warnings.append("stt_not_run: audio extracted for Whisper fallback")
        frames = extract_frames(media_path, frames_dir, duration_seconds=actual_duration, detail=manifest.detail)
        manifest.frame_candidates = frames
        manifest.frames = "extracted" if frames else "missing"
        manifest.media = "provided"
        manifest.evidence_status = "partial_extraction" if frames or audio_path else "metadata_only"

    paths = {
        "manifest": str(root / "manifest.json"),
        "metadata": str(video_dir / "metadata.json"),
        "transcript": str(video_dir / "transcript.md"),
        "extract": str(root / "02-extract.md"),
    }
    (video_dir / "metadata.json").write_text(json.dumps(manifest.metadata, indent=2), encoding="utf-8")
    transcript_status = "unavailable" if manifest.transcript == "unavailable" else "missing"
    (video_dir / "transcript.md").write_text(f"# Transcript\n\nStatus: {transcript_status}\n", encoding="utf-8")
    (root / "02-extract.md").write_text(
        "# Hermes Video evidence extract\n\n"
        f"Source: {request.source_url}\n"
        f"Platform: {request.platform}\n"
        f"Detail: {manifest.detail}\n"
        f"Evidence status: {manifest.evidence_status}\n\n"
        + ("Frames extracted for visual review.\n" if manifest.frames == "extracted" else "No transcript or frames have been extracted yet. This bundle is a planned evidence pass only.\n"),
        encoding="utf-8",
    )
    analysis_ready = _write_analysis_ready(root, manifest)
    paths["analysis_ready"] = str(analysis_ready)
    manifest.write_json(paths["manifest"])
    return paths
