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

## Initial scope

This first commit establishes the repo, contracts, and tested frame-budget/cue logic. Next implementation slices add ffmpeg extraction, transcript adapters, OCR, YouTube wiring, and System B integration tests.
