from __future__ import annotations

import argparse
import json

from .bundle import write_workspace_bundle
from .models import VideoEvidenceManifest, VideoEvidenceRequest
from .planner import frame_budget, select_detail_defaults


def _parse_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    parts = value.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise argparse.ArgumentTypeError(f"invalid timestamp: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan a Hermes Video evidence pass.")
    parser.add_argument("source_url")
    parser.add_argument("--platform", default="unknown")
    parser.add_argument("--detail", choices=["quick", "balanced", "deep", "focused", "full"], default="balanced")
    parser.add_argument("--duration", type=float, default=0.0, help="Known duration for planning")
    parser.add_argument("--manifest", help="Optional path to write manifest JSON")
    parser.add_argument("--workspace", help="Optional System B workspace to seed with a Hermes Video bundle")
    parser.add_argument("--media-path", help="Optional already recovered local video path")
    parser.add_argument("--start", type=_parse_timestamp, help="Focused range start")
    parser.add_argument("--end", type=_parse_timestamp, help="Focused range end")
    args = parser.parse_args(argv)

    if args.workspace:
        request = VideoEvidenceRequest(
            source_url=args.source_url,
            platform=args.platform,
            media_path=args.media_path,
            detail=args.detail,
            start=args.start,
            end=args.end,
            workspace=args.workspace,
        )
        paths = write_workspace_bundle(request, args.workspace, duration_seconds=args.duration or None)
        print(json.dumps({"workspace": args.workspace, "paths": paths}, indent=2))
        return 0

    defaults = select_detail_defaults(args.detail, focused=args.detail == "focused" or args.start is not None or args.end is not None)
    budget = frame_budget(args.duration, args.detail, focused=args.detail == "focused" or args.start is not None or args.end is not None)
    manifest = VideoEvidenceManifest(
        source_url=args.source_url,
        platform=args.platform,
        detail=args.detail,
        warnings=[] if args.duration else ["duration_unknown: frame budget is provisional"],
        metadata={"planning_defaults": defaults, "planned_frame_budget": budget},
    )
    if args.manifest:
        manifest.write_json(args.manifest)
    print(json.dumps(manifest.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
