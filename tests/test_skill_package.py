from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "skills" / "media" / "hermes-video" / "SKILL.md"
REFERENCE_PATH = SKILL_PATH.parent / "references" / "system-b-contract.md"


def _frontmatter_and_body(path: Path):
    content = path.read_text()
    assert content.startswith("---\n")
    marker = "\n---\n"
    end = content.find(marker, 4)
    assert end != -1
    frontmatter = yaml.safe_load(content[4:end])
    body = content[end + len(marker) :]
    return frontmatter, body


def test_hermes_video_skill_is_packaged_with_required_frontmatter():
    assert SKILL_PATH.exists()
    frontmatter, body = _frontmatter_and_body(SKILL_PATH)

    assert frontmatter["name"] == "hermes-video"
    assert frontmatter["description"].startswith("Use when")
    assert len(frontmatter["description"]) <= 1024
    assert "media" in frontmatter["metadata"]["hermes"]["tags"]
    assert "video" in frontmatter["metadata"]["hermes"]["tags"]
    assert "Hermes Video" in body


def test_hermes_video_skill_contains_operational_contract():
    _, body = _frontmatter_and_body(SKILL_PATH)

    required_phrases = [
        "python -m hermes_video.cli doctor --json",
        "python -m hermes_video.cli watch",
        "python -m hermes_video.cli canary",
        "--detail quick",
        "--detail balanced",
        "--detail focused",
        "--timestamps",
        "System B",
        "analysis-ready.md",
        "manifest.json",
        "no transcript + no frames is never `full`",
    ]
    for phrase in required_phrases:
        assert phrase in body


def test_hermes_video_skill_has_progressive_reference_for_system_b_contract():
    assert REFERENCE_PATH.exists()
    reference = REFERENCE_PATH.read_text()

    assert "summary" in reference
    assert "evidence_status" in reference
    assert "frame_count" in reference
    assert "warnings" in reference
    assert "System B" in reference
