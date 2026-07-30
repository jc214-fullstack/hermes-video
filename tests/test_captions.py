from hermes_video import parse_captions, segments_to_markdown

VTT = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello and <b>welcome</b>

00:00:03.000 --> 00:00:05.500
as you can see this repo has the command
"""

SRT = """1
00:00:01,000 --> 00:00:03,000
Hello and welcome

2
00:00:03,000 --> 00:00:05,500
install this tool
"""


def test_parse_vtt_strips_tags_and_keeps_timestamps():
    segments = parse_captions(VTT)
    assert [s["text"] for s in segments] == ["Hello and welcome", "as you can see this repo has the command"]
    assert segments[0]["start"] == 1.0
    assert segments[1]["end"] == 5.5


def test_parse_srt_drops_sequence_indices():
    segments = parse_captions(SRT)
    assert [s["text"] for s in segments] == ["Hello and welcome", "install this tool"]
    assert segments[1]["start"] == 3.0


def test_parse_captions_dedups_rolling_lines():
    rolling = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nsame line\n\n00:00:02.000 --> 00:00:03.000\nsame line\n"
    assert len(parse_captions(rolling)) == 1


def test_segments_to_markdown_includes_source_and_count():
    md = segments_to_markdown(parse_captions(VTT), source="captions")
    assert "Source: captions" in md
    assert "Segments: 2" in md
