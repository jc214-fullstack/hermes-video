# Hermes Video foundation handoff

Hermes Video is now a foundational video-analysis evidence engine for Hermes. This repo is devwork, but the current baseline is coherent: it duplicates the useful Claude Video `/watch` evidence-prep workflow without taking on downstream delivery, editing, or memory-writeback responsibilities.

## Current baseline

Hermes Video accepts URL/local video requests through `watch` and natural `/watch`-style text through `invoke`. It prepares deterministic evidence bundles with:

- metadata and source summary
- captions/transcript, including STT fallback when requested
- timestamped frame evidence
- focused range/user timestamp frames
- transcript-cue frames
- OCR and contact sheet support
- exact/perceptual near-duplicate frame accounting
- stable `manifest.json`
- compact `analysis-ready.md`
- honest evidence statuses: `full`, `partial_extraction`, `metadata_only`, `blocked`, or `needs_review`

The project has passing tests, offline canaries, a documented live/source parity matrix, and a sanitized public sample output bundle.

## What this repo is

This repo is the shareable development baseline for Hermes Video as a Claude Video-equivalent evidence layer.

It is meant to be understandable from:

1. `README.md`
2. `public/docs/claude-video-parity.md`
3. `public/docs/live-parity-matrix.md`
4. `public/examples/claude-video-parity-sample/`
5. `public/docs/testing.md`

## What this repo is not

The current baseline intentionally does not include:

- final Discord/media-analysis delivery formatting
- System B automation wiring
- GBrain/ObiVault writeback
- OwnLight88 editing/rendering handoff
- platform account/session recovery
- manual public-release/security audit

Those are downstream or future integration layers. They do not block this foundation.

## Operator note

Generated workspaces, downloaded videos, frames, contact sheets, canary reports, `.hermes/`, local prompts, and package/cache outputs are ignored and should stay out of git. Public examples should remain text-only and sanitized unless a binary artifact is explicitly reviewed for sharing.
