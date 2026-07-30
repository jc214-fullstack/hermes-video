import json
import subprocess

from hermes_video import fetch_metadata, pick_caption_lang
from hermes_video.downloader import download_captions, download_media


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_fetch_metadata_normalizes_yt_dlp_json():
    raw = {
        "title": "Demo", "channel": "Chan", "duration": 42,
        "webpage_url": "https://x/y", "extractor_key": "Youtube",
        "subtitles": {"en": [{}]}, "automatic_captions": {"en": [{}], "fr": [{}]},
    }
    meta = fetch_metadata("https://x/y", run=lambda argv: _proc(stdout=json.dumps(raw)))
    assert meta["blocked"] is False
    assert meta["title"] == "Demo"
    assert meta["uploader"] == "Chan"
    assert meta["has_native_captions"] is True
    assert meta["auto_caption_langs"] == ["en", "fr"]


def test_fetch_metadata_blocked_on_failure():
    meta = fetch_metadata("https://x/y", run=lambda argv: _proc(returncode=1, stderr="ERROR: private video"))
    assert meta["blocked"] is True
    assert "private video" in meta["error"]


def test_pick_caption_lang_prefers_manual_english():
    assert pick_caption_lang({"subtitle_langs": ["es", "en"], "auto_caption_langs": ["fr"]}) == "en"
    assert pick_caption_lang({"subtitle_langs": [], "auto_caption_langs": ["fr", "en"]}) == "en"
    assert pick_caption_lang({"subtitle_langs": [], "auto_caption_langs": []}) is None


def test_download_captions_returns_written_vtt(tmp_path):
    def fake_run(argv):
        (tmp_path / "vid.en.vtt").write_text("WEBVTT\n")
        return _proc()

    result = download_captions("https://x/y", tmp_path, run=fake_run)
    assert result is not None and result.suffix == ".vtt"


def test_download_media_returns_none_when_blocked(tmp_path):
    assert download_media("https://x/y", tmp_path, run=lambda argv: _proc(returncode=1)) is None
