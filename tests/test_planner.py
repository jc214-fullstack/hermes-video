from hermes_video import DetailMode, cue_frame_timestamps, frame_budget, select_detail_defaults


def test_balanced_frame_budget_scales_by_duration():
    assert frame_budget(10, DetailMode.BALANCED) == 12
    assert frame_budget(45, DetailMode.BALANCED) == 40
    assert frame_budget(120, DetailMode.BALANCED) == 60
    assert frame_budget(900, DetailMode.BALANCED) == 100


def test_detail_modes_expose_expected_defaults():
    assert select_detail_defaults("quick")["max_frames"] == 0
    assert select_detail_defaults("balanced")["strategy"] == "scene_or_keyframe"
    assert select_detail_defaults("deep")["ocr"] is True
    assert select_detail_defaults("full")["max_frames"] is None


def test_focused_budget_is_dense_for_short_ranges():
    assert frame_budget(4, "focused", focused=True) >= 10
    assert frame_budget(20, "focused", focused=True) == 60


def test_cue_frame_timestamps_extract_visual_moments():
    segments = [
        {"start": 1.0, "text": "intro"},
        {"start": 7.5, "text": "as you can see this repo has the command"},
        {"timestamp_seconds": 12, "text": "install this tool"},
    ]
    assert cue_frame_timestamps(segments) == [7.5, 12.0]
