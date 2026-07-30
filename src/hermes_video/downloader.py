"""yt-dlp media + subtitle download. Only invoked when visual/STT evidence is needed."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

Runner = Callable[[list[str]], subprocess.CompletedProcess]


def _default_runner(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def download_captions(url: str, out_dir: str | Path, *, lang: str = "en", auto: bool = True, run: Runner = _default_runner) -> Path | None:
    """Download captions as VTT. Returns the newest .vtt written, or None."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    argv = [
        "yt-dlp", "--skip-download", "--write-subs",
        "--sub-langs", lang, "--sub-format", "vtt", "--convert-subs", "vtt",
        "-o", str(out / "%(id)s.%(ext)s"), url,
    ]
    if auto:
        argv.insert(3, "--write-auto-subs")
    proc = run(argv)
    if proc.returncode != 0:
        return None
    vtts = sorted(out.glob("*.vtt"), key=lambda p: p.stat().st_mtime)
    return vtts[-1] if vtts else None


def download_media(url: str, out_dir: str | Path, *, run: Runner = _default_runner) -> Path | None:
    """Download best mp4-ish media. Returns the media path, or None if blocked."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    template = str(out / "%(id)s.%(ext)s")
    proc = run([
        "yt-dlp", "--no-playlist",
        "-f", "bv*+ba/b", "--merge-output-format", "mp4",
        "-o", template, url,
    ])
    if proc.returncode != 0:
        return None
    media = [p for p in sorted(out.iterdir(), key=lambda p: p.stat().st_mtime)
             if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".m4v"}]
    return media[-1] if media else None
