# System B integration

Hermes Video is consumed by System B as the reusable video evidence layer.

System B keeps platform-specific source recovery in `hermes-j214-customizations/features/system-b-media-analysis`:

- YouTube/Shorts: route directly into Hermes Video after metadata/caption discovery.
- Instagram reels: recover `video_url` or local MP4 through embed/contextJSON/downloader, then call Hermes Video.
- TikTok/Facebook/direct video: call Hermes Video once media bytes exist.
- Reddit/X: call Hermes Video only for actual attached/recovered video. For screenshots, use OCR/partial identity resolvers instead.

Hermes Video owns transcript + visual evidence preparation. System B owns source identity, platform rules, artifact verification, Graphify handoff, Discord delivery, writeback, and digest.

## Manifest contract (System B ingest)

`write_workspace_bundle` returns paths and writes `manifest.json`. System B reads these stable fields without knowing internals:

- `evidence_status` — `full` (transcript + visuals), `partial_extraction`, `metadata_only`, `blocked`, `needs_review`. Hard rule: no transcript + no frames is never `full`.
- `transcript` / `transcript_source` — status (`captions`/`stt`/`unavailable`/`missing`) and where it came from (`captions`, `stt`, `none`).
- `frames` — `extracted`/`missing`/`skipped`; `frame_candidates[]` carry `timestamp_seconds`, `reason` (`uniform`/`transcript_cue`), and `cue_text` when forced by a transcript cue.
- `ocr` — `extracted`/`empty`/`unavailable`; text lands in `video/ocr.md`.
- `contact_sheet` — `imagemagick`/`pil`/`unavailable`; image at `video/contact-sheet.jpg`.
- `media` — `provided`/`downloaded`/`skipped`/`blocked`/`missing`.
- `metadata.frames_candidate_count`, `metadata.frames_selected`, `metadata.frames_dropped_duplicate`, `metadata.cue_frames` — frame selection/dedup accounting.
- `warnings[]` — honest degradation notes (STT not run, tool missing, provisional budget).

Bundle files: `manifest.json`, `video/metadata.json`, `video/transcript.md`, `video/ocr.md`, `video/contact-sheet.jpg`, `video/frames/*.jpg`, `02-extract.md`, `analysis-ready.md`.

Transcript order: local VTT/SRT captions first (`--captions-file` or yt-dlp), then local `faster-whisper` STT (`--stt`) on extracted 16 kHz mono audio. No STT backend keeps the run `partial_extraction` with a warning rather than failing.
