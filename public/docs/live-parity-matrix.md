# Live parity matrix

This matrix records the current Claude Video parity proof for Hermes Video. It is intentionally evidence-prep focused: `/watch`-style source handling, captions/STT, media download only when needed, visual frames, OCR/contact sheet where requested, dedup/status accounting, and honest blocked/partial reporting.

Run date: 2026-08-01

## Summary

| Case | Source | Command surface | Result | Notes |
| --- | --- | --- | --- | --- |
| Captioned YouTube quick | `https://www.youtube.com/watch?v=Ptd860T66WY` | `invoke` | `partial_extraction` | Captions recovered; media/frames skipped by quick mode; warnings empty. |
| Captioned YouTube balanced | `https://www.youtube.com/watch?v=Ptd860T66WY` | `invoke` | `full` | Captions recovered; media downloaded; 15 frames extracted; perceptual dedup backend active; warnings empty. |
| YouTube Shorts-style URL | `https://www.youtube.com/shorts/1FUcniACzmc` | `invoke` | `partial_extraction` | 54s source resolved by yt-dlp; captions recovered; quick mode skipped media/frames; warnings empty. |
| No-caption YouTube + STT | `https://www.youtube.com/watch?v=wwIt5ZvROrs` | `watch --stt` | `partial_extraction` | No manual or automatic captions in metadata; media downloaded; local faster-whisper STT produced transcript; 3 frames extracted; warnings empty. |
| Blocked/unavailable YouTube | intentionally invalid YouTube URL | `invoke` | `blocked` | Metadata/download blocked; final status stayed blocked instead of pretending to watch. |
| Local/direct OCR-heavy sample | synthetic local MP4 + VTT | `watch` | `full` | Captions, visual frame, OCR, contact sheet, and perceptual dedup accounting produced from a generated safe sample. |

## Detailed proof points

### Captioned YouTube quick

Request:

```bash
PYTHONPATH=src python -m hermes_video.cli invoke \
  'watch this video: https://www.youtube.com/watch?v=Ptd860T66WY quick summary, what is this about?' \
  --workspace <workspace>/youtube_quick --json
```

Observed summary:

- `detail=quick`
- `evidence_status=partial_extraction`
- `transcript.status=captions`
- `media.status=skipped`
- `frames.status=skipped`
- `warnings=[]`

### Captioned YouTube balanced

Request:

```bash
PYTHONPATH=src python -m hermes_video.cli invoke \
  '/watch https://www.youtube.com/watch?v=Ptd860T66WY what model/tool claims are shown or said?' \
  --workspace <workspace>/youtube_balanced --json
```

Observed summary:

- `detail=balanced`
- `evidence_status=full`
- `source.title=I Really Liked Opus 5, Then I Used It More...`
- `source.channel=Ben Davis`
- `source.duration_seconds=994.621`
- `transcript.status=captions`
- `media.status=downloaded`
- `frames.status=extracted`
- `frames.count=15`
- `frames.dedup_backend=perceptual`
- `warnings=[]`

### YouTube Shorts-style URL

Request:

```bash
PYTHONPATH=src python -m hermes_video.cli invoke \
  '/watch https://www.youtube.com/shorts/1FUcniACzmc quick summary, what is this short about?' \
  --workspace <workspace>/shorts --json
```

Observed summary:

- `source.title=Make Scroll-Stopping Product Demos with AI I Descript AI`
- `source.duration_seconds=54`
- `evidence_status=partial_extraction`
- `transcript.status=captions`
- `media.status=skipped`
- `frames.status=skipped`
- `warnings=[]`

### No-caption YouTube + STT

Metadata probe for `https://www.youtube.com/watch?v=wwIt5ZvROrs` reported no manual subtitle languages and no automatic caption languages. The STT test therefore used explicit `watch --stt` rather than `invoke`, because `invoke` intentionally has no STT flag yet.

Request:

```bash
PYTHONPATH=src python -m hermes_video.cli watch \
  'https://www.youtube.com/watch?v=wwIt5ZvROrs' \
  --platform youtube --detail balanced --stt \
  --prompt 'summarize this no-caption video from speech if available' \
  --workspace <workspace>/no_caption_stt --json
```

Observed summary:

- `source.title=SaaS Demo Video Example for Fintech Companies`
- `source.duration_seconds=47.981`
- `evidence_status=partial_extraction`
- `transcript.status=stt`
- `transcript.source=stt`
- `media.status=downloaded`
- `frames.status=extracted`
- `frames.count=3`
- `frames.dedup_backend=perceptual`
- `warnings=[]`

### Blocked/unavailable URL

Request used an intentionally invalid YouTube URL.

Observed summary:

- `evidence_status=blocked`
- `transcript.status=missing`
- `media.status=missing`
- `frames.status=skipped`
- warning recorded the upstream YouTube unavailable/metadata failure

This verifies the hard rule: blocked or metadata-only evidence is not reported as a full watch.

### Local/direct OCR-heavy sample

The public sample under `public/examples/claude-video-parity-sample/` was generated from a synthetic local clip and local VTT captions.

Observed summary:

- `evidence_status=full`
- `transcript.status=captions`
- `media.status=provided`
- `frames.status=extracted`
- `frames.count=1`
- `frames.dropped_duplicate=12`
- `frames.dedup_backend=perceptual`
- `ocr.status=extracted`
- `contact_sheet.status=imagemagick`
- `warnings=[]`

## Current interpretation

The live/source matrix now covers the core Claude Video duplicate behavior:

- normal captioned YouTube
- Shorts-style URL handling
- no-caption video with local STT fallback
- blocked/unavailable status honesty
- direct/local media
- OCR/contact-sheet visual evidence
- perceptual frame dedup accounting

Further matrix expansion can add more examples, but these are proof runs rather than missing core functionality.
