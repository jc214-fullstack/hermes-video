---
name: hermes-video
description: Use when a user asks Hermes to watch, inspect, summarize, evidence-check, or hand off a video/short/reel/local clip through the Hermes Video evidence engine instead of doing title/thumbnail-only media analysis.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [media, video, hermes, system-b, evidence, ownlight88]
    related_skills: [ownlight88-shortcut-media-analysis, discord-media-analysis, youtube-content]
---

# Hermes Video

## Overview

Hermes Video is the Hermes-native video evidence layer. It turns a URL, direct media URL, or local video file into a reusable evidence bundle: metadata, transcript/captions, STT status, timestamped frames, OCR text, contact sheet, warnings, and a stable `manifest.json` for downstream Hermes/System B analysis.

Use Hermes Video when the user expects a real video watch. Do not answer from title, thumbnail, platform caption, or URL metadata alone unless the run honestly returns `metadata_only` or `blocked` and you say that visual/transcript evidence was unavailable.

The engine is intentionally evidence-only. It prepares artifacts; Hermes/System B writes interpretation, Discord delivery, artifact verification, GBrain writeback, and final prose.

## When to Use

Use this skill for:

- “Watch this video,” “analyze this reel,” “what happens in this clip,” or “summarize this short.”
- Media-analysis runs that need transcript, frame, OCR, repo/site, command, or visual evidence.
- Focused timestamp questions: “what happens at 0:37,” “look from 1:10 to 1:30,” or “what is shown here.”
- OwnLight88/System B workflows where platform recovery has already produced a local MP4 or direct media URL.
- Verification runs where you need a canary report before trusting the video pipeline.

Do not use this skill for:

- Static screenshots or PDFs; use OCR/document skills instead.
- Final Discord formatting/delivery; System B owns delivery.
- Platform-specific Instagram scraping or account/session recovery; System B recovers media first, then calls Hermes Video.
- Video editing/rendering/remotion composition; that is a separate OwnLight88 editor lane.

## Core Commands

Run from the repo root when developing locally:

```bash
cd /home/dylan-malik/projects/hermes-video-dev

# Preflight dependencies and capability status
PYTHONPATH=src python -m hermes_video.cli doctor --json

# Quick URL pass: metadata/captions first, no media download when captions are enough
PYTHONPATH=src python -m hermes_video.cli watch "https://youtu.be/ID" --platform youtube --detail quick --workspace out/watch --json

# Balanced URL pass: download media when visual evidence is required
PYTHONPATH=src python -m hermes_video.cli watch "https://youtu.be/ID" --platform youtube --detail balanced --workspace out/watch --json

# Local/direct media pass
PYTHONPATH=src python -m hermes_video.cli watch ./clip.mp4 --platform direct --media-path ./clip.mp4 --detail balanced --workspace out/watch --json

# Focused timestamp/range pass
PYTHONPATH=src python -m hermes_video.cli watch ./clip.mp4 --media-path ./clip.mp4 --detail focused --start 0:30 --end 0:45 --timestamps 32,0:38 --workspace out/watch --json

# Deep visual/text pass: denser frames, OCR/contact sheet hooks
PYTHONPATH=src python -m hermes_video.cli watch ./clip.mp4 --media-path ./clip.mp4 --detail deep --prompt "what repo and command are shown" --workspace out/watch --json

# Deterministic offline canaries, with optional live URL gate
PYTHONPATH=src python -m hermes_video.cli canary --report out/canary
PYTHONPATH=src python -m hermes_video.cli canary --live-url "https://youtu.be/ID" --report out/canary
```

If an installed console entry point exists, `hermes-video ...` is equivalent to `PYTHONPATH=src python -m hermes_video.cli ...`.

## Detail Mode Routing

| User intent | Detail mode | Required behavior |
| --- | --- | --- |
| “Summarize this” where captions are likely enough | `quick` | Captions/metadata first; avoid media download when transcript is enough. |
| Normal watch/analyze request | `balanced` | Transcript + visual frames when available. |
| On-screen text, repo, website, code, command, UI, property/video evidence | `deep` | Transcript + denser frames + OCR/contact sheet. |
| User names timestamp/range | `focused` | Force `--timestamps` and/or `--start`/`--end`; manifest must show focused/user frame reasons. |
| User explicitly asks exhaustive visual pass | `full` | Higher-cost whole-video pass; still report limitations honestly. |

Aliases such as `token-burner` should route to the implemented high-detail mode, not invent a separate behavior.

## Evidence Contract

Every successful `watch --json` run should return machine-readable fields that System B can ingest without internal knowledge. The stable artifacts are:

- `manifest.json` — source, status, warnings, evidence status, frame candidates, transcript/OCR/contact-sheet/media state.
- `analysis-ready.md` — compact agent-readable evidence packet.
- `video/metadata.json` — yt-dlp/ffprobe/source metadata where available.
- `video/transcript.md` — captions or STT transcript when available.
- `video/ocr.md` — OCR output or empty/unavailable status.
- `video/contact-sheet.jpg` — visual sheet when generated.
- `video/frames/*.jpg` — timestamped frames with reason metadata.

Hard status rule: no transcript + no frames is never `full`. It must be `metadata_only`, `blocked`, `partial_extraction`, or `needs_review` with warnings.

Frame `reason` values to preserve in manifests/final references: `scene`, `keyframe`, `uniform`, `focused_range`, `user_timestamp`, `transcript_cue`.

See `references/system-b-contract.md` for the exact System B ingest shape.

When working in the `hermes-video-devwork` repo, also read `public/docs/claude-video-parity.md` before parity/design changes, `public/docs/hermes-video-skill-roadmap.md` before skill/system integration changes, and `private/docs` for internal implementation/test notes when available.

## Operating Workflow

1. **Preflight.** Run `python -m hermes_video.cli doctor --json`. Done when required tools for the intended detail mode are present or missing capabilities are explicitly reflected in expected warnings.

2. **Choose source strategy.** For YouTube/Shorts, pass URL directly. For Instagram/Reels/TikTok/Facebook, let System B recover a local MP4/direct URL first when platform auth or embed recovery is needed. Done when the command has either a URL that `yt-dlp` can inspect or a local/direct media path.

3. **Run the watch.** Use `--workspace` for a disposable output directory and `--json` for ingest. Done when the JSON output includes a summary, `manifest.json`, and honest evidence status.

4. **Inspect evidence, not vibes.** Open `analysis-ready.md`, transcript, frame paths/contact sheet, and warnings before answering. Done when every claim in the answer can point back to transcript text, frame reason/timestamp, OCR, or explicit unavailable status.

5. **Hand off to System B.** If this is a media-analysis Discord workflow, System B reads the manifest/summary and owns the final answer. Done when System B records Hermes Video evidence state without relabeling partial evidence as full.

6. **Verify with canaries before broad use.** Run `python -m hermes_video.cli canary --report <out>`. Done when offline canaries report `status: ok`; live URL canary may be `skipped_live_url` unless a live URL was supplied.

## Answering Rules

- State what evidence was actually available: transcript, frames, OCR, contact sheet, blocked, or metadata-only.
- Include important warnings from the manifest when they affect confidence.
- Do not claim “watched” if only metadata/captions were available; say “caption-only” or “metadata-only.”
- For timestamp questions, cite the timestamp/range and whether it came from `user_timestamp`, `focused_range`, or `transcript_cue` frames.
- For on-screen repo/site/command claims, require frame/OCR evidence or label the claim as unverified.

## Common Pitfalls

1. **Calling metadata-only a watch.** Fix: check `evidence_status`, `transcript`, and `frames` before answering.
2. **Downloading video unnecessarily.** Fix: quick mode should use captions/metadata first when that satisfies the request.
3. **Letting Hermes Video own platform recovery.** Fix: System B handles platform identity/recovery; Hermes Video handles media evidence once the source is usable.
4. **Ignoring warnings.** Fix: propagate blocked/STT/OCR/download warnings into the final analysis or handoff.
5. **Committing generated artifacts.** Fix: keep workspaces, frames, videos, caches, and `.hermes/` out of git.
6. **Skipping canaries after pipeline changes.** Fix: run the canary command plus `pytest` before reporting a stable video pipeline.

## Verification Checklist

- [ ] `PYTHONPATH=src python -m hermes_video.cli doctor --json` ran.
- [ ] `PYTHONPATH=src python -m pytest -q` passed for repo changes.
- [ ] `PYTHONPATH=src python -m hermes_video.cli canary --report <out>` reported offline `status: ok`.
- [ ] Real/local CLI smoke wrote `manifest.json` and `analysis-ready.md`.
- [ ] Final answer distinguishes `full`, `partial_extraction`, `metadata_only`, and `blocked` honestly.
- [ ] System B handoff reads stable `summary`/manifest fields rather than scraping prose.
- [ ] Only source/docs/tests/skill files were committed; generated media artifacts stayed untracked or ignored.
