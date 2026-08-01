import json
import shutil

import pytest

from hermes_video.canary import run_canaries, write_report

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe unavailable",
)

REQUIRED = {
    "synthetic_local_video",
    "ocr_text_video",
    "caption_cue_frame",
    "focused_range",
    "duplicate_frames",
    "blocked_url",
    "live_url",
}


def test_offline_canaries_report_shape(tmp_path):
    report = run_canaries(workdir=tmp_path)

    assert set(report) >= {"status", "canaries"}
    names = {c["name"] for c in report["canaries"]}
    assert REQUIRED <= names
    for c in report["canaries"]:
        assert c["status"] in {"passed", "failed", "skipped", "skipped_live_url"}
        assert "detail" in c

    live = next(c for c in report["canaries"] if c["name"] == "live_url")
    assert live["status"] == "skipped_live_url"

    offline = [c for c in report["canaries"] if c["name"] != "live_url"]
    assert all(c["status"] == "passed" for c in offline), [c for c in offline if c["status"] != "passed"]
    assert report["status"] == "ok"


def test_write_report_emits_json_and_markdown(tmp_path):
    report = run_canaries(workdir=tmp_path)
    out = write_report(report, tmp_path / "report")
    assert out["json"].endswith(".json") and out["markdown"].endswith(".md")
    data = json.loads((tmp_path / "report.json").read_text())
    assert data["status"] == report["status"]
    assert "# Hermes Video canary report" in (tmp_path / "report.md").read_text()
