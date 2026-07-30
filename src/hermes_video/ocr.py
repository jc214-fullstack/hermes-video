"""tesseract OCR wrapper. Skips gracefully when tesseract is absent."""
from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which


def ocr_available() -> bool:
    return which("tesseract") is not None


def ocr_image(image_path: str | Path) -> str | None:
    """Return recognized text for one image, or None if OCR is unavailable/failed."""
    if not ocr_available():
        return None
    proc = subprocess.run(
        ["tesseract", str(image_path), "stdout"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def ocr_frames(frames: list[str | Path]) -> list[dict]:
    """OCR a list of frame paths; only non-empty results are returned."""
    results: list[dict] = []
    for frame in frames:
        text = ocr_image(frame)
        if text:
            results.append({"path": str(frame), "text": text})
    return results
