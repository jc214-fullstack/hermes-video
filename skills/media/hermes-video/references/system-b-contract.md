# System B contract for Hermes Video

System B consumes Hermes Video as an evidence engine, not as a final-answer writer.

## Recommended invocation

```bash
PYTHONPATH=src python -m hermes_video.cli watch <SOURCE> \
  --platform <youtube|direct|generic> \
  --media-path <LOCAL_MP4_IF_RECOVERED> \
  --detail <quick|balanced|deep|focused|full> \
  --prompt "<user question>" \
  --workspace <SYSTEM_B_RUN_DIR>/hermes-video \
  --json
```

Use `--timestamps` and/or `--start`/`--end` for user-specific time questions.

## Stable `watch --json` fields

System B should ingest the `summary` block and the manifest path rather than scraping prose.

Expected fields:

- `workspace` — output directory for this Hermes Video run.
- `manifest_path` or `paths.manifest` — path to `manifest.json`.
- `summary.evidence_status` — `full`, `partial_extraction`, `metadata_only`, `blocked`, or `needs_review`.
- `summary.transcript.status` — `captions`, `stt`, `unavailable`, or `missing`.
- `summary.transcript.source` — `captions`, `stt`, or `none`.
- `summary.transcript.path` — transcript markdown path when written.
- `summary.frames.status` — `extracted`, `missing`, or `skipped`.
- `summary.frames.frame_count` — selected frame count after dedup.
- `summary.frames.paths` — frame artifact paths when included.
- `summary.ocr.status` — `extracted`, `empty`, or `unavailable`.
- `summary.ocr.path` — OCR markdown path when written.
- `summary.contact_sheet.status` — `imagemagick`, `pil`, or `unavailable`.
- `summary.contact_sheet.path` — contact-sheet image path when written.
- `summary.media.status` — `provided`, `downloaded`, `skipped`, `blocked`, or `missing`.
- `summary.media.path` — local media path when known.
- `summary.warnings` — degradation/blocker warnings that must survive into System B state.

## Manifest fields System B may inspect

`manifest.json` is the durable evidence contract. System B may read:

- `evidence_status`
- `source`
- `platform`
- `detail`
- `transcript`
- `transcript_source`
- `frames`
- `ocr`
- `contact_sheet`
- `media`
- `warnings[]`
- `frame_candidates[]`
- `metadata.frames_candidate_count`
- `metadata.frames_selected`
- `metadata.frames_dropped_duplicate`
- `metadata.cue_frames`
- `metadata.user_timestamp_frames`
- `metadata.focused_start`
- `metadata.focused_end`

Frame `reason` values are meaningful: `scene`, `keyframe`, `uniform`, `focused_range`, `user_timestamp`, `transcript_cue`.

## Status rules

System B must not upgrade status. In particular, no transcript + no frames is never `full`. If Hermes Video returns `metadata_only`, `blocked`, `partial_extraction`, or `needs_review`, the final media-analysis answer must preserve that limitation.

Use `full` only when Hermes Video produced both transcript evidence and visual frame evidence, or when the manifest's own status is already `full`.

## Boundary

Hermes Video owns transcript/visual evidence preparation. System B owns platform-specific recovery, identity, artifact verification, Discord delivery, final prose, and GBrain/ObiVault writeback.
