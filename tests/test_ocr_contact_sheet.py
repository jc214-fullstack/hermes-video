import shutil

import pytest

from hermes_video.contact_sheet import build_contact_sheet, contact_sheet_backend
from hermes_video.ocr import ocr_available, ocr_image


def _make_text_image(path):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (320, 120), (255, 255, 255))
    ImageDraw.Draw(img).text((10, 40), "HELLO REPO", fill=(0, 0, 0))
    img.save(path)


def test_build_contact_sheet_skips_gracefully_without_frames(tmp_path):
    path, status = build_contact_sheet([], tmp_path / "sheet.jpg")
    assert path is None
    assert status == "no_frames"


@pytest.mark.skipif(contact_sheet_backend() is None, reason="no ImageMagick/PIL")
def test_build_contact_sheet_writes_when_backend_available(tmp_path):
    frames = []
    for i in range(3):
        p = tmp_path / f"f{i}.jpg"
        _make_text_image(p)
        frames.append(p)
    path, status = build_contact_sheet(frames, tmp_path / "sheet.jpg")
    assert path is not None and path.exists()
    assert status in {"imagemagick", "pil"}


@pytest.mark.skipif(not ocr_available(), reason="tesseract unavailable")
def test_ocr_reads_rendered_text(tmp_path):
    img = tmp_path / "text.png"
    _make_text_image(img)
    text = ocr_image(img)
    assert text is not None
    assert "REPO" in text.upper()
