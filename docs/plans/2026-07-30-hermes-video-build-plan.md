# Hermes Video Build Plan

> Goal: build a Hermes-native equivalent of Claude Video `/watch`: a reusable video evidence engine that turns a video URL or local file into transcript + frames + OCR + manifest + analysis-ready bundle for Hermes to read.

## Current baseline

Already made:

- Repo exists: `/home/dylan-malik/projects/hermes-video`.
- CLI entry exists: `hermes-video`.
- Current CLI plans/seeds a workspace bundle only.
- Models exist for `VideoEvidenceRequest`, `VideoEvidenceManifest`, `DetailMode`, `EvidenceStatus`, `FrameCandidate`.
- Planner exists for detail defaults, frame budgets, and cue-frame timestamp detection.
- Tests exist for planner/CLI/bundle contracts.

Missing:

- Real `yt-dlp` metadata/caption extraction.
- Real download path.
- Real `ffprobe` duration/resolution inspection.
- Real `ffmpeg` frame/audio extraction.
- Native captions/transcript parser.
- STT fallback adapter.
- OCR adapter.
- Contact sheet.
- Frame dedup.
- Analysis-ready markdown bundle.
- Doctor/preflight command.
- System B adapter contract.
- Real canaries.

## Product definition

Hermes Video is not the media-analysis system. It only prepares evidence.

Input:

- URL or local file path.
- Prompt/question.
- Detail mode.
- Optional platform.
- Optional start/end/timestamps.
- Workspace output directory.

Output:

- `manifest.json`
- `metadata.json`
- `transcript.md`
- `frames/*.jpg`
- `contact-sheet.jpg`
- `ocr.md`
- `analysis-ready.md`

Hermes then reads those files/images and writes the actual answer.

## Evidence status rules

- `full`: transcript + visual frames/OCR were actually recovered and inspected-ready.
- `partial_extraction`: useful evidence exists, but transcript or visuals are missing.
- `metadata_only`: only title/caption/thumbnail/description metadata exists.
- `blocked`: source cannot be accessed/downloaded.
- `needs_review`: evidence is ambiguous or multiple candidates exist.

Hard rule: no transcript + no frames = never `full`.

## Detail modes

- `quick`: metadata + native transcript/captions when available; no frames by default.
- `efficient`: fast keyframes; low-cost visual pass.
- `balanced`: default; transcript + scene/keyframe frames.
- `deep`: denser frames + OCR/contact sheet.
- `focused`: dense timestamp/range-specific pass.
- `full`: expensive whole-video scene pass only when explicitly requested.

Need add `efficient` alias or mode; current code has quick/balanced/deep/focused/full only.

## Build order

### Slice 1 — CLI command shape + doctor

Build:

- `hermes-video watch SOURCE --prompt "..." --detail balanced --workspace OUT`
- `hermes-video doctor`
- Keep old direct invocation backward-compatible if easy.

Doctor checks:

- `yt-dlp`
- `ffmpeg`
- `ffprobe`
- `tesseract`
- STT backend availability/env

Acceptance:

- CLI tests pass.
- Doctor reports ok/missing/fix-hint for each dependency.

### Slice 2 — yt-dlp metadata/captions

Build modules:

- `downloader.py`
- `captions.py`
- `metadata.py`

Behavior:

- Run `yt-dlp --dump-json` / equivalent safely with argv list.
- Capture title, uploader/channel, duration, webpage_url, description, thumbnail, subtitles/automatic captions, extractor.
- Pull native captions first.
- If quick/transcript mode has captions, do not download video.

Acceptance:

- Fixture/mocked tests for metadata and captions.
- Manifest can be `metadata_only` or `partial_extraction` honestly.

### Slice 3 — media download + ffprobe

Build:

- media download with `yt-dlp` only when visual/STT is needed.
- local path passthrough.
- `ffprobe` duration/resolution/codec.

Acceptance:

- Local fixture video works without network.
- Download blocker produces `blocked`, not exception-only failure.

### Slice 4 — ffmpeg frames/audio

Build:

- audio extraction: mono 16 kHz/low-bitrate audio for STT.
- frame extraction by mode:
  - efficient/keyframes
  - balanced/scene or fallback uniform
  - deep/focused/full budgets
- timestamp naming.

Acceptance:

- Synthetic video fixture generates frames and audio.
- Start/end focused range works.
- Long-video sparse warning is recorded.

### Slice 5 — transcript fallback

Build:

- transcript adapter interface.
- native captions -> `transcript.md`.
- STT fallback from audio.
- graceful unavailable status if no STT backend.

Possible STT backends:

- local `faster-whisper`
- Groq Whisper
- OpenAI Whisper

Default should be graceful unavailable unless backend/env exists.

Acceptance:

- Native captions path works from fixture/mocked captions.
- STT unavailable gives partial status with warning, not failed run.

### Slice 6 — OCR + contact sheet

Build:

- `ocr.py` using CLI `tesseract` first.
- `contact_sheet.py` using ImageMagick if present or PIL fallback if available; otherwise skip gracefully.
- OCR only in deep/focused/full or when prompt asks for on-screen text/repo/site/tool.

Acceptance:

- OCR unavailable does not fail the bundle.
- Contact sheet either writes or records unavailable.

### Slice 7 — frame dedup + cue frames

Build:

- near-duplicate frame dropping.
- selected-vs-candidate counts in manifest.
- cue frames from transcript terms: “look here”, “as you can see”, “github”, “install”, “website”, “tool”, etc.

Acceptance:

- Dedup fixture drops repeated static frames.
- Cue timestamps force relevant frames into selection.

### Slice 8 — analysis-ready bundle

Build `analysis_ready.py`:

- compact markdown with source metadata, evidence status, transcript summary/path, frame list with timestamps, OCR text, warnings, and instructions for Hermes.

Acceptance:

- `analysis-ready.md` is enough for a Hermes agent to inspect the bundle.
- Frame paths are relative/portable from workspace.

### Slice 9 — System B adapter contract

Build:

- stable return JSON for media-analysis to ingest.
- possibly `hermes-video watch ... --json`.

Output fields:

- manifest path
- evidence status
- transcript path/status
- frame paths/count
- OCR path/status
- media path/status
- warnings

Acceptance:

- System B can call Hermes Video and update Manifest v2 without knowing internals.

### Slice 10 — canaries

Canaries:

- local synthetic video.
- local screen recording with text.
- YouTube captioned video.
- YouTube no-caption/forced-STT mocked fallback.
- focused timestamp.
- frame dedup.
- blocked `yt-dlp` URL.
- Instagram reel fallback/blocker shape.

Acceptance:

- `pytest -q` passes.
- One real local video command produces full bundle.
- One real public URL command produces at least metadata/caption bundle or honest blocker.

## Qualifying questions

Only decisions needed before implementation:

1. STT default: should v1 prefer local `faster-whisper`, Groq Whisper, OpenAI Whisper, or graceful-unavailable until configured?
2. Should the CLI use Claude Video naming exactly (`efficient`, `balanced`, `token-burner`) or our current Hermes names (`quick`, `balanced`, `deep`, `focused`, `full`)? My default: support both aliases.
3. Should v1 optimize for YouTube + local files only, then Instagram next? My default: yes.
4. Should Hermes Video include its own answer generation? My default: no, evidence only; Hermes/media-analysis writes final answer.
5. Should we install missing dependencies if absent, or only doctor/report instructions? My default: doctor/report first, no surprise installs.
