# Hermes Video Build Plan

> Goal: build a Hermes-native equivalent of Claude Video `/watch`: a reusable video evidence engine that turns a video URL or local file into transcript + frames + OCR + manifest + analysis-ready bundle for Hermes to read.

## Current baseline

Already made:

- Repo exists: `/home/dylan-malik/projects/hermes-video-dev`.
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

Target behavior: work like Claude Video `/watch`, but for Hermes. It should download/inspect video data, recover transcript, select screenshots/frames from both visual strategy and transcript cues, then hand Hermes a bundle it can review and summarize.

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

Required core deps:

- `yt-dlp` — URL metadata/captions/download.
- `ffmpeg` — audio/frame/contact-sheet prep.
- `ffprobe` — duration/resolution/media inspection.

Required-for-rich-evidence deps:

- `tesseract` — OCR for on-screen text.
- ImageMagick `magick` or Python/PIL fallback — contact sheet.
- best available Whisper/STT backend — transcript fallback when captions are missing.

Auto-install policy:

- Hermes Video may auto-install missing dependencies when the user runs a command that needs them.
- `doctor` must define exactly what is missing and which install command it would run.
- No silent opaque installs: report/install steps in output, but do not block on asking every time.

Acceptance:

- CLI tests pass.
- Doctor reports ok/missing/fix-hint/install command for each dependency.
- Doctor can distinguish already-available deps from install-needed deps.

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

### Slice 5 — transcript fallback + transcript-cue screenshots

Build:

- transcript adapter interface.
- native captions -> `transcript.md`.
- STT fallback from audio.
- graceful unavailable status if no STT backend.
- transcript cue detector that finds moments like:
  - “look at this”
  - “look here”
  - “as you can see”
  - “this repo”
  - “this website”
  - “install this”
  - “watch this part”
- force screenshot/frame extraction around those cue timestamps, with configurable padding before/after.

Possible STT backends:

- local `faster-whisper` when installed/usable.
- Groq Whisper if configured.
- OpenAI Whisper if configured.

Default STT policy:

- Use the best available Whisper-compatible backend.
- Prefer local `faster-whisper` when available for privacy/locality.
- If local is unavailable but Groq/OpenAI env is configured, use the configured external backend.
- If no backend is available, auto-install/configure when the selected mode requires STT and installation is possible; otherwise mark STT unavailable and keep the run partial.

Acceptance:

- Native captions path works from fixture/mocked captions.
- STT unavailable gives partial status with warning, not failed run.
- Transcript cue fixture forces frame paths near cue timestamps into the bundle.
- `analysis-ready.md` explicitly pairs cue text with matching screenshots/frames.

### Slice 6 — OCR + contact sheet

Build:

- `ocr.py` using CLI `tesseract` first.
- `contact_sheet.py` using ImageMagick if present or PIL fallback if available; otherwise skip gracefully.
- OCR only in deep/focused/full or when prompt asks for on-screen text/repo/site/tool.

Acceptance:

- OCR unavailable does not fail the bundle.
- Contact sheet either writes or records unavailable.

### Slice 7 — frame dedup + cue-frame merge

Build:

- near-duplicate frame dropping.
- selected-vs-candidate counts in manifest.
- cue frames from transcript terms: “look at this”, “look here”, “as you can see”, “github”, “install”, “website”, “tool”, etc.
- merge frame sources:
  - detail-mode frames from keyframes/scenes/uniform sampling,
  - user-requested timestamps,
  - transcript-cue screenshots.
- preserve why each frame was selected: `scene`, `keyframe`, `uniform`, `user_timestamp`, `transcript_cue`, `focused_range`.

Acceptance:

- Dedup fixture drops repeated static frames.
- Cue timestamps force relevant frames into selection.
- Manifest records frame reason and source transcript cue where applicable.

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

## Implementation decisions locked

- STT default: use the best available Whisper-compatible backend. Prefer local `faster-whisper` when available; this host already has `faster_whisper` importable.
- Auto-install: Hermes Video may auto-install missing dependencies when needed, but must define/report the deps and install commands through `doctor`.
- Test URL: Mike will provide live URL later; build with local/safe fixtures first.
- Detail naming: support both Claude Video aliases and Hermes names.
- V1 scope: YouTube + local/direct files first, Instagram after.
- Final answer: Hermes Video remains evidence-only. Hermes/System B writes interpretation.

Current host dependency check:

- `yt-dlp`: available at `/home/dylan-malik/.local/bin/yt-dlp`
- `ffmpeg`: available at `/usr/bin/ffmpeg`
- `ffprobe`: available at `/usr/bin/ffprobe`
- `tesseract`: available at `/usr/bin/tesseract`
- `magick`: available at `/usr/bin/magick`
- Python `faster_whisper`: available

## Qualifying questions

Resolved. No blocking questions remain before implementation.