# Hermes Video

Hermes-native video evidence preparation for System B media analysis.

Hermes Video turns a video source into an agent-readable evidence bundle: metadata, transcript status, timestamped frames, OCR hooks, cue-frame hints, warnings, and a manifest that downstream Hermes skills can analyze honestly.

This repo is intentionally separate from `hermes-j214-customizations` so the video engine can become reusable outside OwnLight88's iPhone Shortcut flow. System B consumes it as the video evidence layer.

## Design rules

- Captions/transcript first.
- Download video only when visual evidence or STT is required.
- Every video analysis should try for both transcript and visual evidence.
- Never call title/caption/thumbnail-only work a full watch.
- Keep deterministic media prep in code; keep interpretation in Hermes skills.
- Write stable artifacts that can be inspected, digested, tested, and replayed.

## Detail modes

- `quick` — metadata + transcript/captions when available; no frames unless requested.
- `balanced` — transcript + sampled scene/keyframes; default for normal review.
- `deep` — transcript + denser frames + OCR/contact-sheet hooks.
- `focused` — dense range/timestamp-specific review.
- `full` — high-cost whole-video scene pass only when explicitly requested.

## Current implementation

Hermes Video now has the v1 evidence engine needed by System B:

- `hermes-video watch SOURCE --workspace OUT --detail balanced|deep|focused|full`
- URL metadata/caption discovery through `yt-dlp`
- quick URL mode that uses captions without downloading media
- balanced/deep URL mode that downloads media when visual evidence is needed
- local/direct media `ffprobe`, `ffmpeg` audio extraction, sampled frames, and transcript-cue frames
- native VTT/SRT captions first, optional local faster-whisper STT with `--stt`
- OCR/contact-sheet hooks for rich modes
- deterministic exact-frame dedup and manifest counts
- stable `manifest.json`, `video/metadata.json`, `video/transcript.md`, `analysis-ready.md`, and frame artifacts for Hermes/System B to inspect

Still intentionally out of scope: platform interpretation, artifact verification, Discord delivery, and final prose. System B owns those.
