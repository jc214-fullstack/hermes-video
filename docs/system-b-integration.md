# System B integration

Hermes Video is consumed by System B as the reusable video evidence layer.

System B keeps platform-specific source recovery in `hermes-j214-customizations/features/system-b-media-analysis`:

- YouTube/Shorts: route directly into Hermes Video after metadata/caption discovery.
- Instagram reels: recover `video_url` or local MP4 through embed/contextJSON/downloader, then call Hermes Video.
- TikTok/Facebook/direct video: call Hermes Video once media bytes exist.
- Reddit/X: call Hermes Video only for actual attached/recovered video. For screenshots, use OCR/partial identity resolvers instead.

Hermes Video owns transcript + visual evidence preparation. System B owns source identity, platform rules, artifact verification, Graphify handoff, Discord delivery, writeback, and digest.

## Recommended invocation (System B → Hermes Video)

System B recovers media/URL, then calls Hermes Video and reads the `--json` summary:

```
python -m hermes_video.cli watch <SOURCE> \
  --platform <youtube|direct|instagram|...> \
  --media-path <LOCAL_MP4_IF_ALREADY_RECOVERED> \
  --detail <quick|efficient|balanced|deep|focused|full> \
  --start <SEC> --end <SEC> --timestamps <s,mm:ss,...> \
  --captions-file <VTT/SRT> --stt \
  --workspace <OUT_DIR> --json
```

System B passes either a direct URL or a locally recovered `--media-path`. Hermes
Video never does platform-specific scraping; System B recovers Instagram/TikTok
media and hands over local bytes or a direct URL.

## `--json` summary (stable ingest fields)

`watch --workspace ... --json` prints a stable object. Backward-compatible keys
`workspace` and `paths` are preserved; the `summary` block is the contract:

```json
{
  "workspace": "<OUT_DIR>",
  "paths": {"manifest": "...", "metadata": "...", "transcript": "...", "extract": "...", "analysis_ready": "..."},
  "summary": {
    "workspace": "<OUT_DIR>",
    "manifest_path": "<OUT_DIR>/manifest.json",
    "evidence_status": "full|partial_extraction|metadata_only|blocked|needs_review",
    "transcript": {"status": "captions|stt|unavailable|missing", "source": "captions|stt|none", "path": "<OUT_DIR>/video/transcript.md"},
    "frames": {"status": "extracted|missing|skipped", "count": 13, "paths": ["..."], "selected": 13, "dropped_duplicate": 2},
    "ocr": {"status": "extracted|empty|unavailable", "path": "<OUT_DIR>/video/ocr.md"},
    "media": {"status": "provided|downloaded|skipped|blocked|missing", "path": "<recovered media path or null>"},
    "warnings": ["..."]
  }
}
```

## Manifest contract (System B ingest)

`write_workspace_bundle` returns paths and writes `manifest.json`. System B reads these stable fields without knowing internals:

- `evidence_status` — `full` (transcript + visuals), `partial_extraction`, `metadata_only`, `blocked`, `needs_review`. Hard rule: no transcript + no frames is never `full`.
- `transcript` / `transcript_source` — status (`captions`/`stt`/`unavailable`/`missing`) and where it came from (`captions`, `stt`, `none`).
- `frames` — `extracted`/`missing`/`skipped`; `frame_candidates[]` carry `timestamp_seconds`, `reason`, and `cue_text` when forced by a transcript cue. Frame `reason` values: `scene`, `keyframe`, `uniform` (deterministic fallback), `focused_range` (`--start`/`--end` or focused mode), `user_timestamp` (`--timestamps`), `transcript_cue` (forced by a transcript phrase). Forced frames (`user_timestamp`, `transcript_cue`) are ordered ahead of sampled frames so dedup keeps them over a byte-identical sampled frame.
- `ocr` — `extracted`/`empty`/`unavailable`; text lands in `video/ocr.md`.
- `contact_sheet` — `imagemagick`/`pil`/`unavailable`; image at `video/contact-sheet.jpg`.
- `media` — `provided`/`downloaded`/`skipped`/`blocked`/`missing`.
- `metadata.frames_candidate_count`, `metadata.frames_selected`, `metadata.frames_dropped_duplicate`, `metadata.cue_frames`, `metadata.user_timestamp_frames`, `metadata.focused_start`/`focused_end` — frame selection/dedup accounting and focused-range provenance.
- `warnings[]` — honest degradation notes (STT not run, tool missing, provisional budget).

Bundle files: `manifest.json`, `video/metadata.json`, `video/transcript.md`, `video/ocr.md`, `video/contact-sheet.jpg`, `video/frames/*.jpg`, `02-extract.md`, `analysis-ready.md`.

Transcript order: local VTT/SRT captions first (`--captions-file` or yt-dlp), then local `faster-whisper` STT (`--stt`) on extracted 16 kHz mono audio. No STT backend keeps the run `partial_extraction` with a warning rather than failing.

## Frame dedup (v1 = exact hash)

Dedup is deterministic exact-byte SHA-256 hashing (`deduplicate_frame_candidates`).
It drops repeated static frames cheaply with no image-processing dependency, and
records `frames_candidate_count` / `frames_selected` / `frames_dropped_duplicate`
so System B can audit selection. Perceptual/near-duplicate dedup can replace it
later behind the same contract without changing these fields.

## Offline canaries

`python -m hermes_video.cli canary [--live-url URL] [--report PATH]` runs
deterministic local canaries (synthetic video, OCR text card, caption cue frame,
focused range/timestamps, duplicate/static frames, mock blocked URL) and writes
`<PATH>.json` + `<PATH>.md`. Without `--live-url` the live canary reports
`skipped_live_url` rather than fabricating a network success. Exit code is `0`
when no canary failed.
