# Hermes Video skill roadmap

This is the remaining work to turn `hermes-video` from a packaged skill + evidence CLI into a fully Hermes-native video capability.

## Current state

The repo has a working evidence engine, a packaged skill, System B contract docs, tests, and deterministic canaries. The live profile can load `skill_view(name="hermes-video")`.

Current proof points:

- `watch` CLI writes `manifest.json`, `analysis-ready.md`, transcript/frames/OCR/contact-sheet artifacts where available.
- `invoke` CLI parses natural `/watch <url> question` / `watch this video: <url> ...` text into a deterministic request and runs the same engine.
- `doctor` CLI reports local dependency readiness.
- `canary` CLI runs deterministic offline cases.
- Skill exists at `skills/media/hermes-video/SKILL.md` and has `references/system-b-contract.md`.

## Remaining work

### 1. Install/publish surface

Goal: make `hermes-video` easy to install into any Hermes profile, not just this live profile.

Build:

- repo script or documented command to copy/install `skills/media/hermes-video` into a chosen `$HERMES_HOME/skills/media/hermes-video`
- verification that `hermes skills list` or `skill_view(name="hermes-video")` sees it after restart/reload
- version marker/changelog for skill updates

Acceptance gate: a fresh Hermes profile can install the skill and load it without manual file editing.

### 2. Hermes slash command

Goal: expose a Hermes-native `/watch`-style operator path instead of requiring manual CLI commands.

Done so far: the repo-local `invoke` subcommand accepts natural `/watch <url> question` text, infers detail mode, parses ranges/timestamps, and runs the engine into a workspace. This is the deterministic parser layer the gateway needs.

Still to build:

- a Hermes gateway/plugin surface that maps a real operator `/watch` message to `hermes_video.cli invoke`, or
- documented command alias that creates a workspace, runs `invoke --json`, and loads `analysis-ready.md` back into the session.

Acceptance gate: user can ask Hermes to watch a video and Hermes runs the evidence engine automatically with a saved workspace and honest status report.

### 3. System B adapter

Goal: media-analysis should call Hermes Video when video evidence is required.

Build:

- deterministic adapter in System B that shells out to `python -m hermes_video.cli watch ... --json`
- manifest ingestion for `summary.evidence_status`, transcript state, frames state, OCR state, media state, and warnings
- final-answer guard: System B cannot call metadata-only evidence a full watch

Acceptance gate: a System B media-analysis run records Hermes Video evidence status in its own manifest and final answer.

### 4. Live URL canary

Goal: prove the pipeline on a real supplied public URL without fabricating network success.

Build:

- operator command: `python -m hermes_video.cli canary --live-url <URL> --report <OUT>`
- archived JSON/Markdown canary report path
- expected blocked/partial handling for sites that reject download/captions

Acceptance gate: one public URL run is saved as a canary report, or the blocker is recorded honestly.

### 5. Perceptual dedup

Goal: match Claude Video’s near-duplicate suppression more closely.

Build:

- lightweight perceptual hash or image-similarity dedup behind existing manifest fields
- keep exact-hash fallback when optional image deps are missing
- tests proving selected/dropped frame counts stay deterministic

Acceptance gate: static/near-static video drops visually redundant frames without changing the stable manifest contract.

### 6. GBrain/ObiVault writeback

Goal: preserve useful video evidence summaries without committing raw media.

Build:

- optional note writer for source URL, run status, manifest path, transcript path, contact sheet path, key warnings, and final summary
- no raw video/frames in GitHub unless explicitly requested
- source-of-truth remains local artifact paths + manifest

Acceptance gate: completed watches can be indexed/recalled later without leaking raw media or overstating evidence.

### 7. OwnLight88 editing handoff

Goal: hand evidence into the separate OwnLight88 editing/render lane.

Build:

- reference-video analysis output that can become a Format Card
- raw clip evidence output that can seed an EDL/edit plan
- explicit boundary: Hermes Video prepares evidence; Remotion/FFmpeg/OwnLight88 editor renders final videos

Acceptance gate: a reference URL can produce evidence structured enough for the editor workflow to build a format/style plan.

## Near-term order

1. Rename/verify the GitHub repo as `hermes-video-devwork`.
2. Keep docs aligned with Claude Video parity in `public/docs/claude-video-parity.md`.
3. Add System B adapter so media-analysis calls Hermes Video automatically.
4. Add Hermes `/watch` or plugin wrapper.
5. Run a live URL canary supplied by Mike.
6. Add perceptual dedup and optional external STT providers.

## Done definition

The Hermes Video skill is “done” when Hermes can receive a video request, select the right detail mode from the skill, run the evidence engine, produce stable artifacts, ingest those artifacts through System B or a Hermes command, and answer only from verified transcript/frame/OCR evidence.
