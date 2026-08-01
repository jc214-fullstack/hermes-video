# Testing Hermes Video

Hermes Video has three verification layers: unit/contract tests, deterministic canaries, and real watch smoke tests.

## Unit and contract tests

Run from repo root:

```bash
PYTHONPATH=src python -m pytest -q
```

This proves the planner, CLI contracts, frame reasons, System B JSON shape, skill packaging, public/private repo layout, and deterministic canary logic. It also covers the native `/watch` text parser (`tests/test_invoke.py`), the summary `source` metadata block and duration-warning cleanup (`tests/test_summary_and_duration.py`), and rolling auto-caption cleanup (`tests/test_captions.py`).

## Native `/watch` invocation

`invoke` turns natural text into a deterministic request and runs the same engine:

```bash
PYTHONPATH=src python -m hermes_video.cli invoke \
  "/watch https://youtu.be/ID from 0:30 to 0:45 what repo and command are shown" \
  --workspace /tmp/hermes-video-invoke --json
```

Expected: JSON with an `invocation` block (parsed `source`, `prompt`, `detail`,
`start`/`end`, `timestamps`), a `summary` block, and a workspace containing
`manifest.json` and `analysis-ready.md`. A bare URL/path with no detail hint
defaults to `balanced`; a timestamp/range routes to `focused`; on-screen/repo/code
wording routes to `deep`.

## Dependency doctor

```bash
PYTHONPATH=src python -m hermes_video.cli doctor --json
```

Use this before rich video work. It should report local availability for `yt-dlp`, `ffmpeg`, `ffprobe`, OCR/contact-sheet tooling, and STT capability.

## Offline canaries

```bash
PYTHONPATH=src python -m hermes_video.cli canary --report /tmp/hermes-video-canary
```

Expected healthy shape:

- `status: ok`
- local synthetic video passes
- OCR text-card canary passes or records the expected dependency limitation
- caption cue-frame canary passes
- focused range/user timestamp canary passes
- duplicate/static frame canary passes
- blocked URL canary passes
- live URL canary reports `skipped_live_url` unless `--live-url` is supplied

## Local synthetic CLI smoke

Use a generated clip plus VTT captions to prove the full artifact bundle without relying on network conditions.

Expected evidence:

- `manifest.json` exists
- `analysis-ready.md` exists
- transcript status is `captions` or `stt`
- frames are extracted when visual mode is selected
- cue frame count is recorded when caption cue phrases exist
- evidence status is honest: no transcript + no frames is never `full`

## Live URL canary

When Mike supplies a URL:

```bash
PYTHONPATH=src python -m hermes_video.cli canary --live-url "<URL>" --report /tmp/hermes-video-live-canary
```

Do not fabricate success. If the source blocks captions/media, preserve `blocked`, `metadata_only`, or `partial_extraction` with warnings.

## Git hygiene gate

Before commit:

```bash
git diff --check
git status --short
```

Generated videos, frames, canary reports, `.hermes/`, `.pytest_cache/`, and runtime prompts stay out of commits. Public/shareable docs go under `public/docs/`; internal planning and test notes go under `private/docs/`.
