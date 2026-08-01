# Private test notes

Use this as the operator checklist when deciding whether Hermes Video actually works.

## Fast local gate

```bash
PYTHONPATH=src python -m pytest -q
```

Expected: all tests pass.

## Dependency gate

```bash
PYTHONPATH=src python -m hermes_video.cli doctor --json
```

Expected: doctor reports dependency status honestly. Missing optional dependencies should produce warnings/fix hints, not silent fake success.

## Canary gate

```bash
PYTHONPATH=src python -m hermes_video.cli canary --report /tmp/hermes-video-canary
```

Expected: `status: ok`, `failed: 0`, and `live_url` is `skipped_live_url` unless a URL is provided.

## local synthetic CLI smoke

Create a small temporary clip and VTT file, then run a focused/deep watch command. Verify:

- `manifest.json` exists
- `analysis-ready.md` exists
- transcript exists and status is captions or STT
- frames exist for visual modes
- `cue_frames` increments for transcript-cue text
- `user_timestamp` and `focused_range` reasons appear when requested
- no transcript + no frames is never `full`

## native /watch invocation smoke

Prove the text-parsing path runs the same engine:

```bash
PYTHONPATH=src python -m hermes_video.cli invoke \
  "/watch ./clip.mp4 from 0:01 to 0:04 what repo and command are shown on screen" \
  --workspace /tmp/hermes-video-invoke --json
```

Verify:

- `invocation.detail` is `focused` (range present); `start`/`end` parsed.
- `invocation.source` is the URL/path; `prompt` has command filler stripped.
- workspace has `manifest.json` and `analysis-ready.md`.
- with a real local clip, `summary.warnings` no longer carries `duration_unknown` (ffprobe cleared it).

## live URL canary

When Mike supplies a test URL:

```bash
PYTHONPATH=src python -m hermes_video.cli canary --live-url "<URL>" --report /tmp/hermes-video-live-canary
```

Expected: either live evidence succeeds, or blocked/partial status is recorded with warnings. Do not fabricate live success.

## System integration gate

After the System B adapter or Hermes slash command exists, test the full path:

1. Send a video request through the Hermes-facing surface.
2. Confirm Hermes Video workspace is created.
3. Confirm System B/command reads `summary` and `manifest.json`.
4. Confirm final response names evidence status and warnings.
5. Confirm metadata-only evidence is not described as a full watch.

## Git/public-private gate

Before push:

```bash
git diff --check
git status --short
```

Public docs belong in `public/docs/`. Private docs and internal test notes belong in `private/docs/`. Generated artifacts stay ignored.
