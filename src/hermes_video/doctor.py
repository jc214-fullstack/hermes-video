"""Dependency doctor for Hermes Video."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.util import find_spec
from shutil import which as default_which
from typing import Callable

WhichFn = Callable[[str], str | None]
ImportChecker = Callable[[str], bool]


def _default_import_checker(module: str) -> bool:
    return find_spec(module) is not None


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    kind: str
    status: str
    required: bool
    path: str | None = None
    install_hint: str = ""
    purpose: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_DEPENDENCIES = (
    {"name": "yt-dlp", "kind": "command", "required": True, "purpose": "URL metadata/captions/download", "install_hint": "Install yt-dlp: python3 -m pip install --user -U yt-dlp or pipx install yt-dlp"},
    {"name": "ffmpeg", "kind": "command", "required": True, "purpose": "audio/frame extraction", "install_hint": "Install ffmpeg: sudo apt-get install ffmpeg"},
    {"name": "ffprobe", "kind": "command", "required": True, "purpose": "duration/resolution/codecs", "install_hint": "Install ffmpeg/ffprobe: sudo apt-get install ffmpeg"},
    {"name": "tesseract", "kind": "command", "required": False, "purpose": "OCR for on-screen text", "install_hint": "Install tesseract: sudo apt-get install tesseract-ocr"},
    {"name": "magick", "kind": "command", "required": False, "purpose": "contact sheet generation", "install_hint": "Install ImageMagick: sudo apt-get install imagemagick"},
    {"name": "faster-whisper", "module": "faster_whisper", "kind": "python", "required": False, "purpose": "local Whisper-compatible STT fallback", "install_hint": "Install faster-whisper: python3 -m pip install --user -U faster-whisper"},
)


def check_dependencies(*, which: WhichFn = default_which, import_checker: ImportChecker = _default_import_checker) -> tuple[DependencyStatus, ...]:
    results: list[DependencyStatus] = []
    for dep in _DEPENDENCIES:
        if dep["kind"] == "command":
            path = which(str(dep["name"]))
            status = "ok" if path else "missing"
        else:
            path = None
            status = "ok" if import_checker(str(dep["module"])) else "missing"
        results.append(
            DependencyStatus(
                name=str(dep["name"]),
                kind=str(dep["kind"]),
                status=status,
                required=bool(dep["required"]),
                path=path,
                install_hint="" if status == "ok" else str(dep["install_hint"]),
                purpose=str(dep["purpose"]),
            )
        )
    return tuple(results)


def dependency_report(*, which: WhichFn = default_which, import_checker: ImportChecker = _default_import_checker) -> dict[str, object]:
    deps = check_dependencies(which=which, import_checker=import_checker)
    missing_required = [dep.name for dep in deps if dep.required and dep.status != "ok"]
    return {
        "status": "missing_required" if missing_required else "ok",
        "missing_required": missing_required,
        "dependencies": [dep.to_dict() for dep in deps],
    }
