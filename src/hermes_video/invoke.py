"""Turn natural `/watch` text into a deterministic Hermes Video request.

Parses invocations like:

- ``/watch https://youtu.be/ID what is this about?``
- ``watch this video: https://youtu.be/ID from 0:30 to 0:45``
- ``analyze ./clip.mp4 what repo and command are shown``

into a :class:`WatchInvocation` (source, prompt, detail, timestamps, range)
and runs the existing evidence engine. No agent layer, no network of its own.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .bundle import build_system_b_summary, write_workspace_bundle
from .models import VideoEvidenceRequest
from .planner import normalize_detail_mode

_URL_RE = re.compile(r"https?://\S+", re.I)
_LOCAL_PATH_RE = re.compile(r"\S+\.(?:mp4|mov|mkv|webm|m4v|avi|mpg|mp3|wav|m4a|flac)\b", re.I)
_TS = r"\d{1,2}:\d{2}(?::\d{2})?|\d+(?:\.\d+)?s?"
_RANGE_RE = re.compile(rf"\bfrom\s+({_TS})\s+(?:to|until|through|-|–|—)\s+({_TS})\b", re.I)
_AT_RE = re.compile(rf"\bat\s+({_TS})\b", re.I)
_LEAD_COMMANDS = re.compile(
    r"^\s*(?:/watch(?:-text)?|/hermes-video)\b[:,]?\s*",
    re.I,
)
# Only a *leading* command verb is filler; the same words mid-prompt are the
# user's actual question ("summarize the intro").
_FILLER = re.compile(
    r"^\s*(?:can you |could you |please |go |now )?"
    r"(?:watch|analyze|analyse|summari[sz]e|inspect|review|check|look at|evidence[- ]?check|hand ?off)"
    r"\s+(?:this |the |that )?(?:video|clip|reel|short|footage|source|file)?\s*[:,-]?\s*",
    re.I,
)

_FULL_HINTS = ("exhaustive", "token-burner", "token burner", "every frame", "whole video", "entire video")
_DEEP_HINTS = (
    "on screen", "on-screen", "onscreen", "repo", "repository", "github", "code", "command",
    "website", "site", "install", "ocr", "text on", "what is shown", "shown on screen", "ui ",
    "screenshot", "url", "read the",
)
_QUICK_HINTS = ("quick", "tl;dr", "tldr", "just the transcript", "transcript only", "caption only", "gist")


def _seconds(token: str) -> float:
    tok = token.strip()
    if ":" not in tok and tok.lower().endswith("s"):
        tok = tok[:-1]
    if ":" in tok:
        parts = [float(p) for p in tok.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return float(tok)


def _infer_detail(text: str, *, has_timestamps: bool) -> str:
    lowered = text.lower()
    if any(hint in lowered for hint in _FULL_HINTS):
        return "full"
    if has_timestamps:
        return "focused"
    if any(hint in lowered for hint in _DEEP_HINTS):
        return "deep"
    if any(hint in lowered for hint in _QUICK_HINTS):
        return "quick"
    return "balanced"


def _platform_for(source: str, is_local: bool) -> str:
    if is_local:
        return "direct"
    lowered = source.lower()
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return "youtube"
    return "direct" if "://" in lowered else "unknown"


@dataclass(frozen=True)
class WatchInvocation:
    raw_text: str
    source: str | None
    prompt: str
    detail: str
    platform: str
    is_local: bool = False
    start: float | None = None
    end: float | None = None
    timestamps: tuple[float, ...] = ()
    workspace: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["timestamps"] = list(self.timestamps)
        return data

    def to_request(self, workspace: str | None = None) -> VideoEvidenceRequest:
        if self.source is None:
            raise ValueError("no video source found in text; ask the user for a URL or file path")
        ws = workspace or self.workspace
        return VideoEvidenceRequest(
            source_url=self.source,
            platform=self.platform,
            media_path=self.source if self.is_local else None,
            prompt=self.prompt,
            detail=self.detail,
            start=self.start,
            end=self.end,
            timestamps=self.timestamps,
            workspace=ws,
        )


def parse_watch_text(text: str, *, default_detail: str | None = None, workspace: str | None = None) -> WatchInvocation:
    raw = text
    body = _LEAD_COMMANDS.sub("", text).strip()

    url_match = _URL_RE.search(body)
    source: str | None = None
    is_local = False
    if url_match:
        source = url_match.group(0).rstrip(").,;\"'")
    else:
        path_match = _LOCAL_PATH_RE.search(body)
        if path_match:
            source = path_match.group(0).rstrip(").,;\"'")
            is_local = True

    start = end = None
    range_match = _RANGE_RE.search(body)
    if range_match:
        start, end = _seconds(range_match.group(1)), _seconds(range_match.group(2))
    timestamps: list[float] = []
    for at_match in _AT_RE.finditer(body):
        timestamps.append(_seconds(at_match.group(1)))

    has_ts = start is not None or end is not None or bool(timestamps)
    detail = default_detail or _infer_detail(body, has_timestamps=has_ts)
    detail = normalize_detail_mode(detail)

    prompt = body
    if source:
        prompt = prompt.replace(source, " ")
    prompt = _FILLER.sub(" ", prompt)
    prompt = _RANGE_RE.sub(" ", prompt)
    prompt = _AT_RE.sub(" ", prompt)
    prompt = re.sub(r"\s+", " ", prompt).strip(" :,-").strip()

    return WatchInvocation(
        raw_text=raw,
        source=source,
        prompt=prompt,
        detail=detail,
        platform=_platform_for(source or "", is_local),
        is_local=is_local,
        start=start,
        end=end,
        timestamps=tuple(timestamps),
        workspace=workspace,
    )


def run_invocation(text: str, workspace: str, *, default_detail: str | None = None, duration_seconds: float | None = None) -> dict:
    """Parse ``text`` and run the evidence engine into ``workspace``."""
    invocation = parse_watch_text(text, default_detail=default_detail, workspace=workspace)
    request = invocation.to_request(workspace)
    paths = write_workspace_bundle(request, workspace, duration_seconds=duration_seconds)
    summary = build_system_b_summary(workspace, paths)
    return {
        "invocation": invocation.to_dict(),
        "workspace": workspace,
        "paths": paths,
        "summary": summary,
    }
