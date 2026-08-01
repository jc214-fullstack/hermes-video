"""Hermes Video evidence preparation package."""
from .bundle import build_planned_manifest, build_system_b_summary, write_workspace_bundle
from .captions import parse_captions, segments_to_markdown
from .invoke import WatchInvocation, parse_watch_text, run_invocation
from .metadata import fetch_metadata, pick_caption_lang
from .models import DetailMode, EvidenceStatus, FrameCandidate, VideoEvidenceRequest, VideoEvidenceManifest
from .planner import cue_frame_segments, cue_frame_timestamps, frame_budget, select_detail_defaults
from .stt import transcribe_audio, whisper_available

__all__ = [
    "DetailMode",
    "EvidenceStatus",
    "FrameCandidate",
    "VideoEvidenceRequest",
    "VideoEvidenceManifest",
    "build_planned_manifest",
    "build_system_b_summary",
    "write_workspace_bundle",
    "parse_captions",
    "segments_to_markdown",
    "WatchInvocation",
    "parse_watch_text",
    "run_invocation",
    "fetch_metadata",
    "pick_caption_lang",
    "frame_budget",
    "cue_frame_segments",
    "cue_frame_timestamps",
    "select_detail_defaults",
    "transcribe_audio",
    "whisper_available",
]
