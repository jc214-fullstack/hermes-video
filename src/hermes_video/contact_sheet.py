"""Contact-sheet montage via ImageMagick, with a PIL fallback, else skip."""
from __future__ import annotations

import subprocess
from math import ceil, sqrt
from pathlib import Path
from shutil import which


def contact_sheet_backend() -> str | None:
    if which("magick") or which("montage"):
        return "imagemagick"
    if _has_pil():
        return "pil"
    return None


def _has_pil() -> bool:
    from importlib.util import find_spec

    return find_spec("PIL") is not None


def build_contact_sheet(frames: list[str | Path], output_path: str | Path, *, columns: int | None = None) -> tuple[Path | None, str]:
    """Build a contact sheet from frame images.

    Returns ``(path, status)``; status is ``"imagemagick"``/``"pil"`` on success
    or ``"unavailable"``/``"error:..."``. Never raises.
    """
    frame_paths = [str(f) for f in frames if Path(f).exists()]
    if not frame_paths:
        return None, "no_frames"
    cols = columns or max(1, ceil(sqrt(len(frame_paths))))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    backend = contact_sheet_backend()
    if backend == "imagemagick":
        montage = "magick" if which("magick") else "montage"
        argv = ([montage, "montage"] if montage == "magick" else [montage])
        argv += ["-tile", f"{cols}x", "-geometry", "+4+4", *frame_paths, str(output)]
        proc = subprocess.run(argv, capture_output=True, text=True)
        if proc.returncode == 0 and output.exists():
            return output, "imagemagick"
        return None, f"error:{(proc.stderr or 'montage_failed').strip()[:80]}"
    if backend == "pil":
        try:
            return _pil_sheet(frame_paths, output, cols), "pil"
        except Exception as exc:
            return None, f"error:{type(exc).__name__}"
    return None, "unavailable"


def _pil_sheet(frame_paths: list[str], output: Path, cols: int) -> Path:
    from PIL import Image

    thumbs = [Image.open(p).convert("RGB") for p in frame_paths]
    cw = max(t.width for t in thumbs)
    ch = max(t.height for t in thumbs)
    rows = ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * cw, rows * ch), (16, 16, 16))
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * cw, (i // cols) * ch))
    sheet.save(output, "JPEG", quality=85)
    return output
