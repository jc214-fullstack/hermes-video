from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = ROOT / "public" / "docs"
PRIVATE_DOCS = ROOT / "private" / "docs"
README = ROOT / "README.md"
SKILL = ROOT / "skills" / "media" / "hermes-video" / "SKILL.md"


def test_public_private_doc_tree_exists_and_routes_docs():
    assert PUBLIC_DOCS.exists()
    assert PRIVATE_DOCS.exists()

    public_docs = {
        path.relative_to(PUBLIC_DOCS).as_posix()
        for path in PUBLIC_DOCS.rglob("*.md")
    }
    private_docs = {
        path.relative_to(PRIVATE_DOCS).as_posix()
        for path in PRIVATE_DOCS.rglob("*.md")
    }

    assert {
        "README.md",
        "claude-video-parity.md",
        "system-b-integration.md",
        "hermes-video-skill-roadmap.md",
        "testing.md",
    }.issubset(public_docs)
    assert {
        "README.md",
        "current-state.md",
        "implementation-workplan.md",
        "test-notes.md",
        "plans/2026-07-30-hermes-video-build-plan.md",
    }.issubset(private_docs)


def test_legacy_docs_root_is_not_the_shareable_source_of_truth():
    legacy_docs = ROOT / "docs"
    assert not legacy_docs.exists()


def test_readme_and_skill_point_to_public_docs_and_private_workspace():
    readme = README.read_text()
    skill = SKILL.read_text()

    for text in (readme, skill):
        assert "public/docs/claude-video-parity.md" in text
        assert "public/docs/hermes-video-skill-roadmap.md" in text
        assert "private/docs" in text


def test_private_docs_describe_remaining_work_and_testing_gates():
    workplan = (PRIVATE_DOCS / "implementation-workplan.md").read_text()
    test_notes = (PRIVATE_DOCS / "test-notes.md").read_text()

    for phrase in [
        "Hermes slash command",
        "System B adapter",
        "live URL canary",
        "perceptual dedup",
        "install/publish surface",
    ]:
        assert phrase in workplan

    for phrase in [
        "pytest -q",
        "doctor --json",
        "canary --report",
        "local synthetic CLI smoke",
        "live URL canary",
    ]:
        assert phrase in test_notes
