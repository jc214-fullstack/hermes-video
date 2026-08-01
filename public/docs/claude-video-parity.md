# Claude Video parity for Hermes Video

Hermes Video should mimic the useful Claude Video work without becoming a Claude plugin. The target is a Hermes-native equivalent of the Claude Video `/watch` pattern: prepare reliable video evidence, then let Hermes/System B reason from that evidence.

## Claude Video `/watch` pattern

The Claude Video reference workflow is compact and disciplined:

1. Accept a URL, local video, prompt, detail mode, optional timestamps, and optional start/end range.
2. Run captions first, because a transcript is usually the cheapest useful evidence.
3. download only what is needed. A caption-only request should not fetch full media bytes unless visual evidence, STT, OCR, or focused frames are needed.
4. Let detail modes control cost/fidelity: transcript/quick, efficient, balanced, deep/token-burner, focused, full.
5. Scale frame budgets by duration and selected mode.
6. Use scene/keyframe extraction with uniform fallback so the agent sees meaningful moments even when scene detection fails.
7. Apply near-duplicate frame suppression so static videos do not waste context on identical screenshots.
8. Let transcript-cue timestamps force frames at phrases like “look here,” “as you can see,” “this repo,” “install this,” and “watch this part.”
9. Use Whisper/STT fallback only when captions are missing and transcript evidence is needed.
10. Never write a final answer from title/description/thumbnail alone as if the video was watched.

## Hermes-native equivalent

Hermes Video implements that evidence-prep shape through a repo CLI and Hermes skill.

Explicit form (`watch`):

```bash
PYTHONPATH=src python -m hermes_video.cli watch <SOURCE> \
  --prompt "<question>" \
  --detail <quick|efficient|balanced|deep|focused|full> \
  --start <SEC_OR_MMSS> --end <SEC_OR_MMSS> \
  --timestamps <s,mm:ss,...> \
  --workspace <OUT_DIR> \
  --json
```

Natural `/watch` form (`invoke`) — the Hermes-native equivalent of typing `/watch URL question`:

```bash
PYTHONPATH=src python -m hermes_video.cli invoke \
  "/watch https://youtu.be/ID from 0:30 to 0:45 what repo and command are shown" \
  --workspace <OUT_DIR> --json
```

`invoke` deterministically extracts the source URL/path, the prompt, the detail
mode (inferred from the words, e.g. on-screen/repo/code → `deep`, any
timestamp/range → `focused`, "quick"/"transcript only" → `quick`), and any
`from X to Y` range or `at X` timestamps, then runs the same evidence engine.

The Hermes version differs from Claude Video in the ownership boundary:

| Layer | Claude Video pattern | Hermes Video design |
| --- | --- | --- |
| Agent surface | Claude `/watch` skill | Hermes `hermes-video` skill / future Hermes command |
| Evidence engine | watch scripts | `src/hermes_video` CLI/package |
| Platform recovery | mostly watch/downloader | System B recovers platform-specific media; Hermes Video receives URL/local media |
| Output | files for Claude to inspect | stable `manifest.json`, `analysis-ready.md`, transcript, frames, OCR, contact sheet |
| Final answer | Claude writes from evidence | Hermes/System B writes from evidence and preserves status honesty |

## Implemented parity

Current Hermes Video already covers the main `/watch` evidence mechanics:

- captions first
- URL metadata/caption discovery through `yt-dlp`
- quick mode that avoids media download when captions are enough
- local/direct media support
- media download path for visual modes
- `ffprobe` metadata
- `ffmpeg` audio and frame extraction
- detail modes including focused ranges and user timestamps
- frame reasons: `scene`, `keyframe`, `uniform`, `focused_range`, `user_timestamp`, `transcript_cue`
- transcript-cue screenshots
- STT fallback hook through local faster-whisper when requested/available
- OCR/contact-sheet hooks
- near-duplicate frame suppression: a Pillow average-hash (aHash) perceptual pass drops visually redundant sampled frames within a small Hamming threshold, with an exact-hash fallback when Pillow is absent, reported via `frames_dedup_backend`/`frames_dropped_duplicate`; explicitly forced frames (user timestamps, transcript cues) are exempt from perceptual dropping
- rolling YouTube auto-caption cleanup so overlapping caption lines collapse into readable transcript segments while preserving timestamps
- provisional `duration_unknown` warning is cleared once yt-dlp/ffprobe report a real duration
- stable System B `watch --json` summary, including a top-level `source` block (title/uploader/channel/duration_seconds) when metadata is available
- natural `/watch` text parsing via the `invoke` subcommand
- offline canary runner
- Hermes skill packaged as `hermes-video`

Live baseline: `https://www.youtube.com/watch?v=Ptd860T66WY` — quick/balanced/deep
runs reached honest caption-only / full evidence status, and the follow-ups from
that run (stale duration warning, missing summary source metadata, noisy
auto-captions) are now fixed.

## Parity status

The Claude Video `/watch` evidence mechanics above are all implemented,
including near-duplicate frame suppression. The evidence-prep feature scope is
at parity: a caller can run the equivalent of `/watch URL question` and get
transcript + visual evidence, or an honest `partial_extraction` / `blocked` /
`metadata_only` status, from stable artifacts.

## Beyond Claude Video parity (not required for parity)

These are Hermes ecosystem integrations and conveniences, not Claude Video
`/watch` features. They are intentionally out of scope for parity and tracked
separately in `hermes-video-skill-roadmap.md`; none of them block the parity
claim above:

- **Hermes slash gateway.** The repo-local `invoke` subcommand already parses natural `/watch URL question` text; a user-facing Hermes gateway/plugin that routes a real operator `/watch` message into it is a Hermes-surface convenience, not a Claude Video feature.
- **System B adapter.** Automated media-analysis wiring that calls Hermes Video and ingests `summary`/`manifest.json`. The stable ingest contract exists; the adapter is a System B concern.
- **Live URL canary.** Offline canaries pass; a supplied public URL can additionally prove live YouTube/caption/media behavior.
- **External STT providers.** Local faster-whisper is supported; Groq/OpenAI Whisper routing can be added later if needed.
- **Skill distribution.** A repeatable install/publish path for other Hermes profiles.
- **GBrain/ObiVault writeback and OwnLight88 editing handoff.** Downstream note-keeping and video-editing lanes that consume evidence; explicitly not part of the evidence engine.
