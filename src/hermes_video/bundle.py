from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from .captions import load_captions, segments_to_markdown
from .contact_sheet import build_contact_sheet
from .downloader import download_captions, download_media
from .media_extract import deduplicate_frame_candidates, extract_audio, extract_frames, extract_frames_at_timestamps, ffprobe_media
from .metadata import fetch_metadata, pick_caption_lang
from .models import VideoEvidenceManifest, VideoEvidenceRequest
from .ocr import ocr_available, ocr_frames
from .planner import cue_frame_segments, frame_budget, normalize_detail_mode, select_detail_defaults
from .stt import transcribe_audio, whisper_available

_OCR_MODES = {"deep", "focused", "full"}
_OCR_PROMPT_HINTS = ("text", "repo", "repository", "github", "website", "site", "url", "install", "command", "code", "screen")
_RICH_MODES = {"deep", "focused", "full"}


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


def _resolve_transcript(request: VideoEvidenceRequest, audio_path: Path | None, manifest: VideoEvidenceManifest) -> tuple[list[dict], str, str]:
    """Return ``(segments, source, status)`` using captions first, then STT."""
    if request.captions_path and Path(request.captions_path).exists():
        segments = load_captions(request.captions_path)
        if segments:
            return segments, "captions", "captions"
        manifest.warnings.append("captions_empty: caption file parsed to zero segments")
    if request.enable_stt and audio_path:
        segments, status = transcribe_audio(audio_path)
        if status == "stt":
            return segments, "stt", "stt"
        manifest.warnings.append(f"stt_{status}: local Whisper produced no transcript")
        return [], "none", "unavailable"
    if audio_path and whisper_available():
        manifest.warnings.append("stt_available_not_run: pass --stt to transcribe extracted audio locally")
    return [], "none", "unavailable"


def _wants_ocr(detail: str, prompt: str) -> bool:
    if detail in _OCR_MODES:
        return True
    prompt_lower = prompt.lower()
    return any(hint in prompt_lower for hint in _OCR_PROMPT_HINTS)


def _write_analysis_ready(root: Path, manifest: VideoEvidenceManifest, *, ocr_hits: list[dict]) -> Path:
    target = root / "analysis-ready.md"
    frame_lines = []
    for frame in manifest.frame_candidates:
        rel = Path(frame.path or "")
        try:
            rel = rel.relative_to(root)
        except ValueError:
            pass
        cue = f" — cue: \"{frame.cue_text}\"" if frame.cue_text else ""
        frame_lines.append(f"- {frame.timestamp_seconds:.3f}s — `{rel.as_posix()}` — reason: {frame.reason}{cue}")
    ocr_lines = [f"- `{Path(hit['path']).name}`: {hit['text'][:200]}" for hit in ocr_hits]
    target.write_text(
        "# Hermes Video analysis-ready bundle\n\n"
        f"Source: {manifest.source_url}\n"
        f"Platform: {manifest.platform}\n"
        f"Detail: {manifest.detail}\n"
        f"Evidence status: {manifest.evidence_status}\n"
        f"Transcript status: {manifest.transcript} (source: {manifest.transcript_source})\n"
        f"Frame status: {manifest.frames}\n"
        f"OCR status: {manifest.ocr}\n"
        f"Contact sheet: {manifest.contact_sheet}\n\n"
        "## Timestamped frames\n\n"
        + ("\n".join(frame_lines) if frame_lines else "No frames extracted.")
        + "\n\n## On-screen text (OCR)\n\n"
        + ("\n".join(ocr_lines) if ocr_lines else "None")
        + "\n\n## Warnings\n\n"
        + ("\n".join(f"- {warning}" for warning in manifest.warnings) if manifest.warnings else "None")
        + "\n\n_Evidence only. Hermes/System B writes the interpretation._\n",
        encoding="utf-8",
    )
    return target


def write_workspace_bundle(request: VideoEvidenceRequest, workspace: str | Path, *, duration_seconds: float | None = None) -> dict[str, str]:
    """Write the Hermes Video workspace contract.

    With a real local ``media_path`` this extracts ffprobe metadata, sampled +
    transcript-cue frames, mono 16 kHz audio, a transcript (captions or local
    STT), OCR, and a contact sheet. Otherwise it writes an honest planned bundle.
    """
    root = Path(workspace)
    video_dir = root / "video"
    frames_dir = video_dir / "frames"
    video_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(exist_ok=True)

    manifest = build_planned_manifest(request, duration_seconds=duration_seconds)
    ocr_hits: list[dict] = []
    transcript_segments: list[dict] = []
    media_path = Path(request.media_path) if request.media_path else None
    source_as_path = Path(request.source_url)
    source_is_local_file = source_as_path.exists()
    if media_path is None and source_is_local_file:
        media_path = source_as_path
        manifest.media = "provided"

    url_metadata: dict = {}
    is_remote_source = "://" in request.source_url and not source_is_local_file
    if is_remote_source:
        url_metadata = fetch_metadata(request.source_url)
        manifest.metadata["url_metadata"] = url_metadata
        if url_metadata.get("blocked"):
            manifest.evidence_status = "blocked"
            manifest.warnings.append(f"metadata_blocked: {url_metadata.get('error', 'yt-dlp metadata failed')}")
        else:
            if url_metadata.get("duration_seconds") and duration_seconds is None:
                manifest.metadata["duration_seconds"] = url_metadata.get("duration_seconds")
            manifest.description = "available" if url_metadata.get("description") else manifest.description
            caption_lang = pick_caption_lang(url_metadata)
            if caption_lang and not request.captions_path:
                caption_path = download_captions(request.source_url, video_dir / "captions", lang=caption_lang)
                if caption_path:
                    request = replace(request, captions_path=str(caption_path))
                    manifest.caption = "downloaded"
                    manifest.metadata["captions_path"] = str(caption_path)
                else:
                    manifest.caption = "unavailable"
                    manifest.warnings.append("captions_download_failed: yt-dlp could not recover captions")

            needs_visual = manifest.detail != "quick"
            if media_path is None and needs_visual and not url_metadata.get("blocked"):
                downloaded = download_media(request.source_url, video_dir / "downloads")
                if downloaded:
                    media_path = downloaded
                    manifest.media = "downloaded"
                    manifest.metadata["downloaded_media_path"] = str(downloaded)
                else:
                    manifest.media = "blocked"
                    manifest.warnings.append("media_download_blocked: yt-dlp could not recover video media")
            elif media_path is None and not needs_visual:
                manifest.media = "skipped"

    if not media_path and request.captions_path:
        transcript_segments, source, status = _resolve_transcript(request, None, manifest)
        manifest.transcript = status
        manifest.transcript_source = source
        if transcript_segments:
            manifest.evidence_status = "partial_extraction"

    if media_path and media_path.exists():
        probe = ffprobe_media(media_path)
        actual_duration = float(probe.get("duration_seconds") or duration_seconds or 0)
        manifest.metadata["probe"] = probe
        manifest.metadata["duration_seconds"] = actual_duration

        audio_path = extract_audio(media_path, video_dir / "audio.wav") if probe.get("has_audio") else None
        manifest.metadata["audio_path"] = str(audio_path) if audio_path else None

        transcript_segments, source, status = _resolve_transcript(request, audio_path, manifest)
        manifest.transcript = status
        manifest.transcript_source = source

        frames = extract_frames(media_path, frames_dir, duration_seconds=actual_duration, detail=manifest.detail)
        cues = cue_frame_segments(transcript_segments)
        cue_frames = extract_frames_at_timestamps(media_path, frames_dir, cues) if cues else []
        all_frames = frames + cue_frames
        candidate_count = len(all_frames)
        all_frames, dropped_duplicates = deduplicate_frame_candidates(all_frames)
        manifest.frame_candidates = all_frames
        manifest.frames = "extracted" if all_frames else "missing"
        if manifest.media != "downloaded":
            manifest.media = "provided"
        manifest.metadata["frames_candidate_count"] = candidate_count
        manifest.metadata["frames_selected"] = len(all_frames)
        manifest.metadata["frames_dropped_duplicate"] = dropped_duplicates
        manifest.metadata["cue_frames"] = len(cue_frames)
        manifest.metadata["cues"] = cues

        if _wants_ocr(manifest.detail, request.prompt) and all_frames:
            if ocr_available():
                targets = [f.path for f in (cue_frames or all_frames) if f.path]
                ocr_hits = ocr_frames(targets)
                manifest.ocr = "extracted" if ocr_hits else "empty"
                (video_dir / "ocr.md").write_text(
                    "# OCR\n\n" + ("\n".join(f"## {Path(h['path']).name}\n\n{h['text']}\n" for h in ocr_hits) or "No on-screen text detected.\n"),
                    encoding="utf-8",
                )
                manifest.metadata["ocr_path"] = str(video_dir / "ocr.md")
            else:
                manifest.ocr = "unavailable"
                manifest.warnings.append("ocr_unavailable: install tesseract for on-screen text")

        if manifest.detail in _RICH_MODES and all_frames:
            sheet_path, sheet_status = build_contact_sheet([f.path for f in all_frames if f.path], video_dir / "contact-sheet.jpg")
            manifest.contact_sheet = sheet_status
            if sheet_path:
                manifest.metadata["contact_sheet_path"] = str(sheet_path)
            elif sheet_status not in {"no_frames"}:
                manifest.warnings.append(f"contact_sheet_{sheet_status}: install ImageMagick or Pillow for contact sheets")

        has_visual = bool(all_frames)
        has_transcript = bool(transcript_segments)
        if has_transcript and has_visual:
            manifest.evidence_status = "full"
        elif has_visual or has_transcript or audio_path:
            manifest.evidence_status = "partial_extraction"
        else:
            manifest.evidence_status = "metadata_only"

    paths = {
        "manifest": str(root / "manifest.json"),
        "metadata": str(video_dir / "metadata.json"),
        "transcript": str(video_dir / "transcript.md"),
        "extract": str(root / "02-extract.md"),
    }
    (video_dir / "metadata.json").write_text(json.dumps(manifest.metadata, indent=2), encoding="utf-8")
    if transcript_segments:
        (video_dir / "transcript.md").write_text(segments_to_markdown(transcript_segments, source=manifest.transcript_source), encoding="utf-8")
    else:
        (video_dir / "transcript.md").write_text(f"# Transcript\n\nStatus: {manifest.transcript}\nSource: {manifest.transcript_source}\n", encoding="utf-8")
    (root / "02-extract.md").write_text(
        "# Hermes Video evidence extract\n\n"
        f"Source: {request.source_url}\n"
        f"Platform: {request.platform}\n"
        f"Detail: {manifest.detail}\n"
        f"Evidence status: {manifest.evidence_status}\n\n"
        + ("Frames extracted for visual review.\n" if manifest.frames == "extracted" else "No transcript or frames have been extracted yet. This bundle is a planned evidence pass only.\n"),
        encoding="utf-8",
    )
    analysis_ready = _write_analysis_ready(root, manifest, ocr_hits=ocr_hits)
    paths["analysis_ready"] = str(analysis_ready)
    manifest.write_json(paths["manifest"])
    return paths
