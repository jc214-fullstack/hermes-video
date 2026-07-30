from hermes_video.planner import normalize_detail_mode, select_detail_defaults


def test_claude_video_detail_aliases_are_supported():
    assert normalize_detail_mode("efficient") == "efficient"
    assert normalize_detail_mode("token-burner") == "full"
    assert normalize_detail_mode("transcript") == "quick"


def test_efficient_detail_uses_keyframe_strategy():
    defaults = select_detail_defaults("efficient")

    assert defaults["mode"] == "efficient"
    assert defaults["strategy"] == "keyframes"
    assert defaults["max_frames"] == 50
