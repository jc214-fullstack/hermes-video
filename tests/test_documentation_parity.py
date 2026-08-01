from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = ROOT / "public" / "docs"
PARITY_DOC = PUBLIC_DOCS / "claude-video-parity.md"
ROADMAP_DOC = PUBLIC_DOCS / "hermes-video-skill-roadmap.md"
README = ROOT / "README.md"


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


def test_readme_points_to_devwork_repo_and_parity_docs():
    text = README.read_text()

    assert "hermes-video-devwork" in text
    assert "public/docs/claude-video-parity.md" in text
    assert "public/docs/hermes-video-skill-roadmap.md" in text
