# Hermes Video

GitHub repo: `jc214-fullstack/hermes-video-devwork`

**A Hermes-native, evidence-first alternative to Claude Video.** Point it at a
video URL or local file and it prepares a reliable, inspectable evidence bundle —
metadata, transcript, timestamped frames, OCR, contact sheet, warnings, and a
stable `manifest.json` — so an agent can reason from what the video *actually*
contains instead of guessing from a title or thumbnail.

Hermes Video only prepares evidence. The interpretation, final prose, and any
delivery are written by the calling agent (Hermes/System B), which keeps the
"was this really watched?" boundary honest.

## Quick start

```bash
# 1. Preflight: what tooling is present and how to install what's missing
PYTHONPATH=src python -m hermes_video.cli doctor --json

# 2a. Natural /watch text — the fastest way in
PYTHONPATH=src python -m hermes_video.cli invoke \
  "/watch https://youtu.be/ID from 0:30 to 0:45 what repo and command are shown" \
  --workspace out/watch --json

# 2b. Explicit form, if you'd rather pass flags
PYTHONPATH=src python -m hermes_video.cli watch "https://youtu.be/ID" \
  --platform youtube --detail balanced --prompt "what is this about?" \
  --workspace out/watch --json
```

Both write the same evidence bundle into the workspace. Read `analysis-ready.md`
and `manifest.json` before trusting any answer.

Requirements: Python 3.11+, `ffmpeg`/`ffprobe`, and `yt-dlp` for URL sources.
`tesseract` (OCR), ImageMagick/Pillow (contact sheets), and `faster-whisper`
(local STT) are optional; `doctor` reports what's available.

## Natural `/watch` invocation

`invoke` turns a plain request into a deterministic engine call — no agent layer,
no hidden network. It extracts:

- the source URL or local file path,
- the prompt (command filler like "watch this video:" is stripped),
- the detail mode, inferred from the words:
  - on-screen / repo / code / command / website → `deep`
  - any `from X to Y` range or `at X` timestamp → `focused`
  - "quick" / "transcript only" → `quick`
  - otherwise → `balanced`
- `from X to Y` ranges and `at X` timestamps.

```bash
PYTHONPATH=src python -m hermes_video.cli invoke "watch this video: https://youtu.be/ID summarize the intro" --workspace out/watch --json
```

Pass `--detail` to override the inferred mode.

## Detail modes

- `quick` — metadata + transcript/captions; no frames unless requested.
- `balanced` — transcript + sampled scene/keyframes; default for normal review.
- `deep` — transcript + denser frames + OCR/contact-sheet hooks.
- `focused` — dense range/timestamp-specific review.
- `full` — high-cost whole-video scene pass only when explicitly requested.

## Design rules

- Captions/transcript first; download video only when visual evidence or STT is required.
- Every analysis tries for both transcript and visual evidence.
- Never call title/caption/thumbnail-only work a full watch.
- Keep deterministic media prep in code; keep interpretation in the calling agent.
- Write stable artifacts that can be inspected, digested, tested, and replayed.

## Evidence contract

Every workspace holds:

- `manifest.json` — source, evidence status, warnings, transcript/frame/OCR/media state, frame candidates.
- `analysis-ready.md` — compact agent-readable evidence packet.
- `video/metadata.json` — yt-dlp/ffprobe/source metadata.
- `video/transcript.md` — captions or STT transcript when available.
- `video/ocr.md`, `video/contact-sheet.jpg`, `video/frames/*.jpg` — visual evidence when generated.

The `watch`/`invoke` JSON `summary` block is what a downstream agent ingests: it
carries `evidence_status`, transcript/frames/OCR/media state, `warnings`, and a
`source` block (title / uploader / channel / duration_seconds) when metadata is
available. The `frames` block reports `selected`, `dropped_duplicate`, and
`dedup_backend` (`perceptual` when Pillow is present, else `exact`). Frame
`reason` values recorded in the manifest: `scene`, `keyframe`, `uniform`
(deterministic fallback), `focused_range`, `user_timestamp`, `transcript_cue`.

Near-duplicate frames are suppressed with a Pillow average-hash perceptual pass
(exact-hash fallback without Pillow); explicitly forced frames (`user_timestamp`,
`transcript_cue`) are never perceptually dropped.

Hard rule: no transcript + no frames is never `full` — it stays
`metadata_only`, `blocked`, `partial_extraction`, or `needs_review`.

See `public/docs/system-b-integration.md` for the full ingest contract.

## Testing

```bash
PYTHONPATH=src python -m pytest -q                                   # unit + contract tests
PYTHONPATH=src python -m hermes_video.cli doctor --json              # dependency readiness
PYTHONPATH=src python -m hermes_video.cli canary --report out/canary # deterministic offline canaries
```

`public/docs/testing.md` documents the verification layers, including the native
`/watch` invocation smoke and the live-URL canary.

## Repo layout

- `src/hermes_video/` — the evidence engine (CLI + package).
- `skills/media/hermes-video/` — the packaged Hermes skill and its System B reference.
- `public/docs/` — shareable documentation (this is the public source of truth).
- `private/docs/` — operator-only implementation notes, plans, and test notes.
- `tests/` — normal project tests.

Generated workspaces, frames, downloaded media, canary reports, `.hermes/`, and
runtime prompts stay out of git.

## Privacy boundary

Anything shareable lives in `README.md`, `public/docs/`, `src/`, `skills/`, and
`tests/`. Operator-only context — internal plans, session notes, private test
notes — lives in `private/docs/`. Generated media and runtime artifacts are
never committed.

## Documentation

- `public/docs/README.md` — public docs index.
- `public/docs/foundation-handoff.md` — concise status/handoff for the devwork baseline.
- `public/docs/claude-video-parity.md` — how the Claude Video `/watch` pattern maps to this implementation.
- `public/docs/live-parity-matrix.md` — live/source proof matrix for captioned YouTube, Shorts-style URLs, no-caption STT, blocked URLs, and local OCR samples.
- `public/examples/claude-video-parity-sample/` — sanitized sample output bundle without raw media.
- `public/docs/system-b-integration.md` — the System B ingest contract.
- `public/docs/testing.md` — verification gates.
- `public/docs/hermes-video-skill-roadmap.md` — remaining skill/system work.
- `private/docs/` — internal plans, private test notes, and operator context.

## Out of scope (intentionally)

Platform interpretation, artifact verification, Discord/delivery formatting,
platform-specific account/session recovery, and video editing/rendering. The
calling agent (Hermes/System B) owns those; Hermes Video stays evidence-only.
