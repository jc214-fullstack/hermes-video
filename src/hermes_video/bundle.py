from __future__ import annotations

import json
from pathlib import Path

from .models import VideoEvidenceManifest, VideoEvidenceRequest
from .planner import frame_budget, select_detail_defaults


def build_planned_manifest(request: VideoEvidenceRequest, *, duration_seconds: float | None = None) -> VideoEvidenceManifest:
    focused = request.detail == "focused" or request.start is not None or request.end is not None
    budget = frame_budget(duration_seconds or 0, request.detail, focused=focused)
    defaults = select_detail_defaults(request.detail, focused=focused)
    media_status = "provided" if request.media_path else "missing"
    warnings: list[str] = []
    if duration_seconds is None:
        warnings.append("duration_unknown: frame budget is provisional")
    if not request.media_path and request.platform not in {"youtube", "direct"}:
        warnings.append("media_path_missing: platform resolver must recover video before visual pass")
    return VideoEvidenceManifest(
        source_url=request.source_url,
        platform=request.platform,
        detail=str(request.detail),
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


def write_workspace_bundle(request: VideoEvidenceRequest, workspace: str | Path, *, duration_seconds: float | None = None) -> dict[str, str]:
    """Write the initial Hermes Video workspace contract.

    This is the stable boundary System B can call before the full ffmpeg/yt-dlp
    adapters land. It records the planned evidence pass without pretending media
    was actually watched.
    """
    root = Path(workspace)
    video_dir = root / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    (video_dir / "frames").mkdir(exist_ok=True)

    manifest = build_planned_manifest(request, duration_seconds=duration_seconds)
    paths = {
        "manifest": str(manifest.write_json(root / "manifest.json")),
        "metadata": str(video_dir / "metadata.json"),
        "transcript": str(video_dir / "transcript.md"),
        "extract": str(root / "02-extract.md"),
    }
    (video_dir / "metadata.json").write_text(json.dumps(manifest.metadata, indent=2), encoding="utf-8")
    (video_dir / "transcript.md").write_text("# Transcript\n\nStatus: missing\n", encoding="utf-8")
    (root / "02-extract.md").write_text(
        "# Hermes Video evidence extract\n\n"
        f"Source: {request.source_url}\n"
        f"Platform: {request.platform}\n"
        f"Detail: {request.detail}\n"
        f"Evidence status: {manifest.evidence_status}\n\n"
        "No transcript or frames have been extracted yet. This bundle is a planned evidence pass only.\n",
        encoding="utf-8",
    )
    return paths
