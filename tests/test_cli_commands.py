import json

from hermes_video.cli import main


def test_doctor_command_prints_json(capsys):
    result = main(["doctor", "--json"])

    assert result in {0, 1}
    data = json.loads(capsys.readouterr().out)
    assert "dependencies" in data
    assert any(item["name"] == "yt-dlp" for item in data["dependencies"])


def test_watch_subcommand_preserves_workspace_bundle_behavior(tmp_path, capsys):
    result = main(["watch", "https://example.com/video.mp4", "--workspace", str(tmp_path), "--detail", "efficient"])

    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert data["workspace"] == str(tmp_path)
    assert (tmp_path / "manifest.json").exists()


def test_legacy_invocation_still_plans_manifest(capsys):
    result = main(["https://example.com/video.mp4", "--duration", "10"])

    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert data["source_url"] == "https://example.com/video.mp4"
