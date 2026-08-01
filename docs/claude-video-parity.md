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

Hermes Video implements that evidence-prep shape through a repo CLI and Hermes skill:

```bash
PYTHONPATH=src python -m hermes_video.cli watch <SOURCE> \
  --prompt "<question>" \
  --detail <quick|efficient|balanced|deep|focused|full> \
  --start <SEC_OR_MMSS> --end <SEC_OR_MMSS> \
  --timestamps <s,mm:ss,...> \
  --workspace <OUT_DIR> \
  --json
```

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
- exact-hash duplicate suppression with selected/dropped counts
- stable System B `watch --json` summary
- offline canary runner
- Hermes skill packaged as `hermes-video`

## Parity gaps / next upgrades

These are the remaining differences from the strongest Claude Video behavior:

1. **Near-duplicate frame suppression.** Hermes has deterministic exact-hash dedup. Claude Video-style near-duplicate/perceptual dedup should be added behind the same manifest fields.
2. **Hermes slash command.** The skill exists, but the user-facing `/watch`-like Hermes command/plugin surface is not wired yet.
3. **System B adapter.** System B still needs a direct adapter that invokes Hermes Video, reads `summary`/`manifest.json`, and inserts evidence state into media-analysis manifests/final answers.
4. **Live URL canary.** Offline canaries pass. A supplied public URL should be used to prove live YouTube/caption/media behavior.
5. **External STT providers.** Local faster-whisper is supported. Groq/OpenAI Whisper routing can be added later if needed.
6. **Skill distribution.** The repo contains the skill and this profile has it installed. We still need a repeatable install/publish path for other Hermes profiles.

## Acceptance standard

Hermes Video reaches true Claude Video feature sync when a Hermes operator can run the equivalent of `/watch URL question`, get transcript + visual evidence or an honest partial/blocked status, and System B can consume the evidence bundle without scraping prose or guessing what happened.
