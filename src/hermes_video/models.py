from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class DetailMode(StrEnum):
    QUICK = "quick"
    EFFICIENT = "efficient"
    BALANCED = "balanced"
    DEEP = "deep"
    FOCUSED = "focused"
    FULL = "full"


class EvidenceStatus(StrEnum):
    FULL = "full"
    PARTIAL_EXTRACTION = "partial_extraction"
    METADATA_ONLY = "metadata_only"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class VideoEvidenceRequest:
    source_url: str
    platform: str = "unknown"
    media_path: str | None = None
    prompt: str = ""
    detail: DetailMode = DetailMode.BALANCED
    start: float | None = None
    end: float | None = None
    timestamps: tuple[float, ...] = ()
    workspace: str | None = None
    captions_path: str | None = None
    enable_stt: bool = False


@dataclass(frozen=True)
class FrameCandidate:
    index: int
    timestamp_seconds: float
    reason: str
    path: str | None = None
    cue_text: str | None = None


@dataclass
class VideoEvidenceManifest:
    source_url: str
    platform: str
    detail: str
    evidence_status: str = EvidenceStatus.PARTIAL_EXTRACTION
    caption: str = "missing"
    media: str = "missing"
    transcript: str = "missing"
    transcript_source: str = "none"
    frames: str = "skipped"
    ocr: str = "unavailable"
    contact_sheet: str = "unavailable"
    description: str = "missing"
    external_verification: str = "none"
    graphify_handoff: str = "not_applicable"
    frame_candidates: list[FrameCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["frame_candidates"] = [asdict(frame) for frame in self.frame_candidates]
        return data

    def write_json(self, path: str | Path) -> Path:
        import json
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return target
