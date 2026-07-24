import json

from hermes_video import VideoEvidenceRequest, build_planned_manifest, write_workspace_bundle


def test_build_planned_manifest_marks_missing_platform_media():
    request = VideoEvidenceRequest(source_url="https://instagram.com/reel/example", platform="instagram")
    manifest = build_planned_manifest(request, duration_seconds=30)
    assert manifest.evidence_status == "metadata_only"
    assert manifest.media == "missing"
    assert any("platform resolver" in warning for warning in manifest.warnings)


def test_write_workspace_bundle_seeds_system_b_contract(tmp_path):
    request = VideoEvidenceRequest(
        source_url="https://youtu.be/example",
        platform="youtube",
        media_path="/tmp/example.mp4",
        detail="balanced",
    )
    paths = write_workspace_bundle(request, tmp_path, duration_seconds=45)
    assert set(paths) == {"manifest", "metadata", "transcript", "extract"}
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["platform"] == "youtube"
    assert manifest["media"] == "provided"
    assert manifest["metadata"]["planned_frame_budget"] == 40
    assert (tmp_path / "video" / "frames").is_dir()
    assert "planned evidence pass" in (tmp_path / "02-extract.md").read_text()
