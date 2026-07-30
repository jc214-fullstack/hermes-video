"""yt-dlp URL metadata + caption discovery (no download)."""
from __future__ import annotations

import json
import subprocess
from typing import Callable

Runner = Callable[[list[str]], subprocess.CompletedProcess]

_CAPTION_LANGS = ("en", "en-US", "en-GB", "en-orig")


def _default_runner(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def fetch_metadata(url: str, *, run: Runner = _default_runner) -> dict:
    """Return normalized metadata for ``url`` using ``yt-dlp -J``.

    On any yt-dlp failure the result is ``{"blocked": True, "error": ...}`` so
    callers can record a ``blocked`` status instead of crashing.
    """
    proc = run(["yt-dlp", "-J", "--no-playlist", "--skip-download", url])
    if proc.returncode != 0:
        return {"blocked": True, "error": (proc.stderr or "yt-dlp failed").strip()}
    try:
        raw = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {"blocked": True, "error": f"unparseable yt-dlp json: {exc}"}
    return normalize_metadata(raw)


def normalize_metadata(raw: dict) -> dict:
    subtitles = raw.get("subtitles") or {}
    auto = raw.get("automatic_captions") or {}
    return {
        "blocked": False,
        "title": raw.get("title"),
        "uploader": raw.get("uploader") or raw.get("channel"),
        "duration_seconds": raw.get("duration"),
        "webpage_url": raw.get("webpage_url") or raw.get("original_url"),
        "description": raw.get("description"),
        "thumbnail": raw.get("thumbnail"),
        "extractor": raw.get("extractor_key") or raw.get("extractor"),
        "has_native_captions": bool(subtitles),
        "has_auto_captions": bool(auto),
        "subtitle_langs": sorted(subtitles.keys()),
        "auto_caption_langs": sorted(auto.keys()),
    }


def pick_caption_lang(meta: dict, preferred: tuple[str, ...] = _CAPTION_LANGS) -> str | None:
    """Choose a caption language, preferring manual English then any available."""
    manual = meta.get("subtitle_langs") or []
    auto = meta.get("auto_caption_langs") or []
    for lang in preferred:
        if lang in manual:
            return lang
    if manual:
        return manual[0]
    for lang in preferred:
        if lang in auto:
            return lang
    return auto[0] if auto else None
