from __future__ import annotations

import argparse
import json

from .models import VideoEvidenceManifest
from .planner import frame_budget, select_detail_defaults


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan a Hermes Video evidence pass.")
    parser.add_argument("source_url")
    parser.add_argument("--platform", default="unknown")
    parser.add_argument("--detail", choices=["quick", "balanced", "deep", "focused", "full"], default="balanced")
    parser.add_argument("--duration", type=float, default=0.0, help="Known duration for planning")
    parser.add_argument("--manifest", help="Optional path to write manifest JSON")
    args = parser.parse_args(argv)

    defaults = select_detail_defaults(args.detail, focused=args.detail == "focused")
    budget = frame_budget(args.duration, args.detail, focused=args.detail == "focused")
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
