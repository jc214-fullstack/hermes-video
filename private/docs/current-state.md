# Current state

Repo: `jc214-fullstack/hermes-video-devwork`

Local path: `/home/dylan-malik/projects/hermes-video-dev`

Purpose: public/shareable Hermes-native video evidence engine plus private workbench notes.

## Verified baseline before this documentation-design pass

- GitHub repo renamed to `hermes-video-devwork`.
- Hermes Video evidence engine exists and supports `doctor`, `watch`, and `canary` commands.
- `hermes-video` skill is packaged in the repo and installed in the active Hermes profile.
- Public docs now live under `public/docs/`.
- Private planning/test notes now live under `private/docs/`.

## Current operational status

Working:

- Captions-first URL/local media evidence flow.
- Detail modes including quick, balanced, deep, focused, and full.
- Focused range/user timestamp frame extraction.
- Transcript-cue frame forcing.
- OCR/contact-sheet hooks.
- Perceptual near-duplicate frame dedup (Pillow aHash, Hamming threshold 4) with exact-hash fallback and `frames_dedup_backend`/`frames_dropped_duplicate` accounting; forced frames exempt from perceptual dropping.
- Stable System B JSON/manifest contract, now with a top-level `source` block (title/uploader/channel/duration_seconds) when metadata is available.
- Native `/watch` text parsing via the `invoke` subcommand: extracts source/prompt, infers detail mode, parses `from X to Y` ranges and `at X` timestamps, and runs the same engine into a workspace.
- Offline deterministic canaries.
- Live YouTube canary baseline using `https://www.youtube.com/watch?v=Ptd860T66WY`: `canary --live-url` passed, quick watch produced caption-only partial evidence, balanced watch produced full evidence with downloaded media/captions/frames, and deep watch produced full evidence with captions/frames/OCR/contact sheet.
- Native `invoke` baseline using the same YouTube URL passed in quick, balanced, deep, and focused text forms. Quick produced caption-only partial evidence; balanced produced full evidence with source title/uploader/duration, downloaded media, captions, and frames; deep produced full evidence with OCR and contact sheet; focused parsed `from 8:20 to 8:55 at 8:30` into `start=500.0`, `end=535.0`, `timestamps=[510.0]`, and produced focused/user timestamp frames.

Live-test follow-ups now resolved:

- `duration_unknown: frame budget is provisional` is cleared once yt-dlp/ffprobe reports a real `duration_seconds`.
- Summary JSON now exposes source title/channel/uploader/duration_seconds so operators can identify the watched source without opening raw metadata.
- YouTube rolling auto-caption lines now collapse into readable transcript segments while preserving timestamps.

Still needed for full Hermes-native use:

- Install/publish surface for the skill across profiles.
- Hermes gateway/plugin that routes a real operator `/watch` message into `invoke` (the deterministic parser layer now exists; the Hermes slash command surface does not).
- System B adapter that calls Hermes Video automatically.
- Live URL canary using a supplied public URL.
- Optional GBrain/ObiVault writeback.
- OwnLight88 editing handoff into Format Card / Remotion / FFmpeg workflow.
