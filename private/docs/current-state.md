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
- Exact-hash frame dedup counts.
- Stable System B JSON/manifest contract.
- Offline deterministic canaries.
- Live YouTube canary baseline using `https://www.youtube.com/watch?v=Ptd860T66WY`: `canary --live-url` passed, quick watch produced caption-only partial evidence, balanced watch produced full evidence with downloaded media/captions/frames, and deep watch produced full evidence with captions/frames/OCR/contact sheet.

Observed live-test follow-ups:

- `duration_unknown: frame budget is provisional` still appears even when ffprobe later records `duration_seconds`; normalize duration warnings after media metadata is known.
- Deep/balanced frame output is functional, but live testing should add summary-level title/channel/duration fields so operators can identify the watched source without opening raw metadata.
- Transcript extraction works, but YouTube auto-caption duplicate segment cleanup should be improved for cleaner reading.

Still needed for full Hermes-native use:

- Install/publish surface for the skill across profiles.
- Hermes slash command or plugin wrapper for `/watch`-style use.
- System B adapter that calls Hermes Video automatically.
- Live URL canary using a supplied public URL.
- Perceptual dedup upgrade.
- Optional GBrain/ObiVault writeback.
- OwnLight88 editing handoff into Format Card / Remotion / FFmpeg workflow.
