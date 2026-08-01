# Implementation workplan

This is the private operator workplan for making Hermes Video fully work as a Hermes skill/system while keeping the repository public-facing and shareable.

## Public/private repo design

Public/shareable surfaces:

- `README.md`
- `public/docs/`
- `src/hermes_video/`
- `skills/media/hermes-video/`
- package metadata and source tests that are safe to share

Private/operator surfaces:

- `private/docs/`
- private test notes
- internal plans
- session-derived notes
- future Claude prompts or handoff specs

Generated media, frames, canary outputs, local workspaces, and `.hermes/` runtime artifacts are neither public docs nor private docs; they stay ignored unless Mike explicitly asks to preserve a sanitized sample.

## Remaining work

### 1. install/publish surface

Build a repeatable installer or documented command that installs `skills/media/hermes-video` into a target Hermes profile. This should avoid manual file editing and verify that `skill_view(name="hermes-video")` resolves after reload/restart.

### 2. Hermes slash command

Build a Hermes slash command or plugin wrapper for `/watch <url-or-path> [question]`. It should create a workspace, call Hermes Video, read `analysis-ready.md`, preserve warnings, and answer only from available evidence.

### 3. System B adapter

Add a System B adapter that shells out to `python -m hermes_video.cli watch ... --json`, reads the `summary` and `manifest.json`, and records evidence status in media-analysis state. The final answer guard must prevent metadata-only results from being called a full watch.

### 4. live URL canary

Run `canary --live-url` with public URLs Mike supplies. Save the JSON/Markdown report privately first, then promote only sanitized proof if useful.

First baseline completed with `https://www.youtube.com/watch?v=Ptd860T66WY`: live canary passed, balanced/deep watch runs reached `evidence_status=full`, captions/media/frames were extracted, and deep mode produced OCR/contact sheet. Follow-up improvements from that run: remove stale duration warnings after ffprobe succeeds, add source title/channel/duration to summary JSON, and clean repeated YouTube auto-caption transcript lines.

### 5. perceptual dedup

Upgrade exact-hash frame dedup to optional perceptual dedup while preserving existing manifest fields. Keep exact-hash as fallback when image dependencies are unavailable.

### 6. GBrain/ObiVault writeback

Add optional writeback that saves source URL, evidence status, manifest path, transcript path, key warnings, and final summary. Do not commit raw video/frames.

### 7. OwnLight88 editing handoff

Define the handoff from Hermes Video evidence to OwnLight88 editing: reference evidence -> Format Card -> raw clip evidence -> edit plan -> Remotion/FFmpeg render. Hermes Video remains evidence-only.

## Acceptance gate

The skill is operational when Hermes can accept a video request, run the evidence engine through the chosen command/plugin/System B path, generate a stable workspace, and produce an answer or handoff that cites real transcript/frame/OCR evidence with honest status.
