# System B integration

Hermes Video is consumed by System B as the reusable video evidence layer.

System B keeps platform-specific source recovery in `hermes-j214-customizations/features/system-b-media-analysis`:

- YouTube/Shorts: route directly into Hermes Video after metadata/caption discovery.
- Instagram reels: recover `video_url` or local MP4 through embed/contextJSON/downloader, then call Hermes Video.
- TikTok/Facebook/direct video: call Hermes Video once media bytes exist.
- Reddit/X: call Hermes Video only for actual attached/recovered video. For screenshots, use OCR/partial identity resolvers instead.

Hermes Video owns transcript + visual evidence preparation. System B owns source identity, platform rules, artifact verification, Graphify handoff, Discord delivery, writeback, and digest.
