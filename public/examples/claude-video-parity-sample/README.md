# Claude Video parity sample output

This directory contains sanitized, shareable examples of Hermes Video output from a synthetic local clip. It does not include raw media, downloaded videos, private paths, credentials, or real user data.

Generated behavior represented here:

- `/watch`-style evidence prep from a local source
- caption transcript ingestion
- visual frame extraction
- OCR/contact-sheet-capable deep mode
- perceptual near-duplicate frame dedup accounting
- honest `evidence_status` in `manifest.sample.json`

Files:

- `manifest.sample.json` — sanitized manifest shape
- `analysis-ready.sample.md` — compact evidence packet Hermes would inspect
- `transcript.sample.md` — transcript artifact
- `ocr.sample.md` — OCR artifact
- `frames-index.sample.md` — frame metadata without committing binary frames

Binary frames/contact sheets are intentionally omitted from the public sample to keep the repo lightweight and shareable.
