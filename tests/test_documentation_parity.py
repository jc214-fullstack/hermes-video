from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = ROOT / "public" / "docs"
PARITY_DOC = PUBLIC_DOCS / "claude-video-parity.md"
ROADMAP_DOC = PUBLIC_DOCS / "hermes-video-skill-roadmap.md"
README = ROOT / "README.md"
FOUNDATION_DOC = PUBLIC_DOCS / "foundation-handoff.md"
SAMPLE_DIR = ROOT / "public" / "examples" / "claude-video-parity-sample"
LIVE_MATRIX = PUBLIC_DOCS / "live-parity-matrix.md"


def test_claude_video_parity_doc_mirrors_reference_workflow():
    text = PARITY_DOC.read_text()

    required = [
        "Claude Video `/watch` pattern",
        "captions first",
        "download only what is needed",
        "detail modes control cost/fidelity",
        "scene/keyframe extraction with uniform fallback",
        "near-duplicate frame suppression",
        "transcript-cue timestamps force frames",
        "Whisper/STT fallback",
        "Hermes-native equivalent",
        "System B",
    ]
    for phrase in required:
        assert phrase in text


def test_skill_roadmap_names_remaining_work_for_hermes_functionality():
    text = ROADMAP_DOC.read_text()

    required = [
        "Install/publish surface",
        "Hermes slash command",
        "System B adapter",
        "live URL canary",
        "perceptual dedup",
        "GBrain/ObiVault writeback",
        "OwnLight88 editing handoff",
        "Acceptance gate",
    ]
    for phrase in required:
        assert phrase in text


def test_roadmap_scopes_integrations_as_beyond_claude_video_parity():
    text = ROADMAP_DOC.read_text().lower()
    # Parity is closed and the remaining integrations are framed as future, not
    # as unmet Claude Video parity requirements.
    assert "parity is the current deliverable and it is closed" in text
    assert "beyond" in text and "claude video parity" in text
    assert "perceptual dedup" in text and "done" in text


def test_parity_doc_marks_near_duplicate_dedup_implemented_and_scopes_extras():
    text = PARITY_DOC.read_text()
    lower = text.lower()
    # Near-duplicate suppression is now claimed as implemented parity, not a gap.
    assert "near-duplicate frame suppression:" in lower
    assert "frames_dedup_backend" in text
    # System B / OwnLight88 are framed as beyond parity, not parity requirements.
    assert "Beyond Claude Video parity (not required for parity)" in text


def test_readme_points_to_devwork_repo_and_parity_docs():
    text = README.read_text()

    assert "hermes-video-devwork" in text
    assert "public/docs/foundation-handoff.md" in text
    assert "public/docs/claude-video-parity.md" in text
    assert "public/docs/live-parity-matrix.md" in text
    assert "public/examples/claude-video-parity-sample/" in text
    assert "public/docs/hermes-video-skill-roadmap.md" in text


def test_foundation_handoff_marks_baseline_without_future_integrations():
    text = FOUNDATION_DOC.read_text()
    required = [
        "foundational video-analysis evidence engine",
        "Claude Video `/watch` evidence-prep workflow",
        "stable `manifest.json`",
        "compact `analysis-ready.md`",
        "does not include",
        "manual public-release/security audit",
    ]
    for phrase in required:
        assert phrase in text


def test_public_sample_output_bundle_is_present_and_sanitized():
    required = [
        "README.md",
        "manifest.sample.json",
        "analysis-ready.sample.md",
        "transcript.sample.md",
        "ocr.sample.md",
        "frames-index.sample.md",
    ]
    for name in required:
        assert (SAMPLE_DIR / name).exists()

    combined = "\n".join((SAMPLE_DIR / name).read_text(errors="replace") for name in required)
    assert "evidence_status" in combined
    assert "analysis-ready" in combined
    assert "frames_dedup_backend" in combined
    assert "/home/dylan-malik" not in combined
    assert "/tmp/hermes-video" not in combined
    assert "[REDACTED]" not in combined


def test_live_parity_matrix_records_core_claude_video_cases():
    text = LIVE_MATRIX.read_text()
    required = [
        "Captioned YouTube quick",
        "Captioned YouTube balanced",
        "YouTube Shorts-style URL",
        "No-caption YouTube + STT",
        "Blocked/unavailable YouTube",
        "Local/direct OCR-heavy sample",
        "frames.dedup_backend=perceptual",
    ]
    for phrase in required:
        assert phrase in text
