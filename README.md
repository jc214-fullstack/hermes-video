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

## Operator commands

Run via the module (or the `hermes-video` entry point):

```
# Preflight: which tools/deps are present and how to install what is missing
python -m hermes_video.cli doctor --json

# Quick URL — captions/metadata only, no media download
python -m hermes_video.cli watch "https://youtu.be/ID" --platform youtube --detail quick --workspace out/ --json

# Balanced URL — downloads media when visual evidence is needed
python -m hermes_video.cli watch "https://youtu.be/ID" --platform youtube --detail balanced --workspace out/ --json

# Local file — direct media, no network
python -m hermes_video.cli watch ./clip.mp4 --platform direct --media-path ./clip.mp4 --detail balanced --workspace out/ --json

# Focused timestamp/range — dense frames in a window plus forced user timestamps
python -m hermes_video.cli watch ./clip.mp4 --media-path ./clip.mp4 --detail focused --start 0:30 --end 0:45 --timestamps 32,0:38 --workspace out/ --json

# Deep — denser frames + OCR + contact sheet for on-screen text / repo / site questions
python -m hermes_video.cli watch ./clip.mp4 --media-path ./clip.mp4 --detail deep --prompt "what repo and command are shown" --workspace out/ --json

# Canary runner — deterministic offline canaries + report; live URL is optional/gated
python -m hermes_video.cli canary --report out/canary
python -m hermes_video.cli canary --live-url "https://youtu.be/ID" --report out/canary

# System B handoff — read the stable summary block from watch --json
python -m hermes_video.cli watch <SOURCE> --media-path <LOCAL_MP4> --detail balanced --workspace out/ --json | jq .summary
```

Frame `reason` values recorded in the manifest: `scene`, `keyframe`, `uniform`
(deterministic fallback), `focused_range`, `user_timestamp`, `transcript_cue`.
See `docs/system-b-integration.md` for the full JSON/manifest contract.

## Hermes skill

This repo packages a Hermes skill at `skills/media/hermes-video/SKILL.md` with a progressively disclosed System B reference at `skills/media/hermes-video/references/system-b-contract.md`.

The skill is the operator surface for deciding when to run Hermes Video, which detail mode to choose, how to preserve evidence-status honesty, and how System B should ingest the stable `watch --json` summary/manifest fields.
