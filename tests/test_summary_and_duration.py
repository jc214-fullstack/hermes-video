import json
from pathlib import Path

from hermes_video.bundle import (
    _DURATION_WARNING,
    _drop_provisional_duration_warning,
    build_planned_manifest,
    build_system_b_summary,
)
from hermes_video.models import VideoEvidenceRequest


def test_planned_manifest_warns_when_duration_unknown():
    manifest = build_planned_manifest(VideoEvidenceRequest(source_url="https://youtu.be/ID"))
    assert _DURATION_WARNING in manifest.warnings


def test_planned_manifest_has_no_duration_warning_when_known():
    manifest = build_planned_manifest(
        VideoEvidenceRequest(source_url="https://youtu.be/ID"), duration_seconds=42.0
    )
    assert _DURATION_WARNING not in manifest.warnings


def test_drop_provisional_duration_warning_is_idempotent():
    manifest = build_planned_manifest(VideoEvidenceRequest(source_url="https://youtu.be/ID"))
    manifest.warnings.append("other_warning: keep me")
    _drop_provisional_duration_warning(manifest)
    _drop_provisional_duration_warning(manifest)
    assert _DURATION_WARNING not in manifest.warnings
    assert "other_warning: keep me" in manifest.warnings


def test_summary_exposes_source_metadata(tmp_path):
    manifest = {
        "source_url": "https://youtu.be/ID",
        "platform": "youtube",
        "evidence_status": "full",
        "transcript": "captions",
        "transcript_source": "captions",
        "frames": "extracted",
        "ocr": "extracted",
        "contact_sheet": "imagemagick",
        "media": "downloaded",
        "warnings": [],
        "frame_candidates": [],
        "metadata": {
            "duration_seconds": 123.4,
            "contact_sheet_path": str(tmp_path / "video" / "contact-sheet.jpg"),
            "url_metadata": {
                "title": "Example clip",
                "uploader": "Example Channel",
                "webpage_url": "https://youtu.be/ID",
            },
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    analysis_ready_path = tmp_path / "analysis-ready.md"
    analysis_ready_path.write_text("# ready", encoding="utf-8")
    summary = build_system_b_summary(
        str(tmp_path), {"manifest": str(manifest_path), "analysis_ready": str(analysis_ready_path)}
    )
    assert summary["analysis_ready_path"] == str(analysis_ready_path)
    source = summary["source"]
    assert source["title"] == "Example clip"
    assert source["uploader"] == "Example Channel"
    assert source["channel"] == "Example Channel"
    assert source["duration_seconds"] == 123.4
    assert source["platform"] == "youtube"
    assert summary["contact_sheet"] == {
        "status": "imagemagick",
        "path": str(tmp_path / "video" / "contact-sheet.jpg"),
    }
