import json

from hermes_video.cli import main
from hermes_video.invoke import parse_watch_text, run_invocation


def test_slash_watch_extracts_url_prompt_and_default_balanced():
    inv = parse_watch_text("/watch https://youtu.be/ID what is this about?")
    assert inv.source == "https://youtu.be/ID"
    assert inv.platform == "youtube"
    assert inv.detail == "balanced"
    assert inv.prompt == "what is this about?"
    assert inv.is_local is False


def test_plain_text_watch_this_video_strips_filler():
    inv = parse_watch_text("watch this video: https://example.com/clip.mp4 summarize the intro")
    assert inv.source == "https://example.com/clip.mp4"
    assert "watch this video" not in inv.prompt
    assert inv.prompt == "summarize the intro"


def test_range_and_at_timestamps_route_to_focused():
    inv = parse_watch_text("watch https://youtu.be/ID from 0:30 to 0:45 and at 1:05 what changes")
    assert inv.detail == "focused"
    assert inv.start == 30.0
    assert inv.end == 45.0
    assert inv.timestamps == (65.0,)
    assert "from" not in inv.prompt and "0:30" not in inv.prompt


def test_deep_hint_infers_deep_detail():
    inv = parse_watch_text("watch ./demo.mp4 what repo and command are shown on screen")
    assert inv.is_local is True
    assert inv.platform == "direct"
    assert inv.detail == "deep"


def test_quick_hint_infers_quick_detail():
    inv = parse_watch_text("quick summary of https://youtu.be/ID just the transcript")
    assert inv.detail == "quick"


def test_detail_override_wins():
    inv = parse_watch_text("watch https://youtu.be/ID show me the code", default_detail="quick")
    assert inv.detail == "quick"


def test_run_invocation_writes_bundle(tmp_path):
    result = run_invocation("watch ./missing-clip.mp4 what is this", str(tmp_path))
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "analysis-ready.md").exists()
    assert result["invocation"]["detail"] == "balanced"
    assert result["summary"]["source"]["platform"] == "direct"


def test_invoke_cli_command_emits_json_and_bundle(tmp_path, capsys):
    result = main(["invoke", "/watch ./missing-clip.mp4 what is this", "--workspace", str(tmp_path)])
    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert data["workspace"] == str(tmp_path)
    assert (tmp_path / "manifest.json").exists()
    assert data["invocation"]["source"] == "./missing-clip.mp4"
