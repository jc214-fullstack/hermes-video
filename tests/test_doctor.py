from hermes_video.doctor import check_dependencies, dependency_report


def test_check_dependencies_reports_required_tools_with_install_commands():
    report = check_dependencies(which=lambda command: f"/usr/bin/{command}" if command in {"yt-dlp", "ffmpeg", "ffprobe"} else None, import_checker=lambda module: module == "faster_whisper")

    by_name = {item.name: item for item in report}

    assert by_name["yt-dlp"].status == "ok"
    assert by_name["ffmpeg"].status == "ok"
    assert by_name["ffprobe"].status == "ok"
    assert by_name["tesseract"].status == "missing"
    assert "install" in by_name["tesseract"].install_hint.lower()
    assert by_name["faster-whisper"].status == "ok"


def test_dependency_report_serializes_for_cli():
    report = dependency_report(which=lambda command: None, import_checker=lambda module: False)

    assert report["status"] == "missing_required"
    assert any(item["name"] == "yt-dlp" and item["required"] for item in report["dependencies"])
    assert any(item["name"] == "tesseract" and not item["required"] for item in report["dependencies"])
