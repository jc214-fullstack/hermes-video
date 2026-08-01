from __future__ import annotations

import argparse
import json

from .bundle import build_system_b_summary, write_workspace_bundle
from .doctor import dependency_report
from .models import VideoEvidenceManifest, VideoEvidenceRequest
from .planner import frame_budget, normalize_detail_mode, select_detail_defaults

_DETAIL_CHOICES = ("transcript", "quick", "efficient", "balanced", "deep", "focused", "full", "token-burner")


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


def _add_watch_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source_url")
    parser.add_argument("--prompt", default="", help="Question/prompt Hermes should answer from the evidence bundle")
    parser.add_argument("--platform", default="unknown")
    parser.add_argument("--detail", choices=_DETAIL_CHOICES, default="balanced")
    parser.add_argument("--duration", type=float, default=0.0, help="Known duration for planning")
    parser.add_argument("--manifest", help="Optional path to write manifest JSON")
    parser.add_argument("--workspace", help="Optional System B workspace to seed with a Hermes Video bundle")
    parser.add_argument("--media-path", help="Optional already recovered local video path")
    parser.add_argument("--start", type=_parse_timestamp, help="Focused range start")
    parser.add_argument("--end", type=_parse_timestamp, help="Focused range end")
    parser.add_argument("--timestamps", help="Comma-separated timestamps (s or mm:ss) to force user_timestamp frames")
    parser.add_argument("--captions-file", help="Local VTT/SRT caption file to use as the transcript")
    parser.add_argument("--stt", action="store_true", help="Run local faster-whisper STT on extracted audio when captions are absent")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON; currently the default output shape")


def _run_watch(args: argparse.Namespace) -> int:
    detail = normalize_detail_mode(args.detail)
    focused = detail == "focused" or args.start is not None or args.end is not None
    timestamps = (
        tuple(_parse_timestamp(t.strip()) for t in args.timestamps.split(",") if t.strip())
        if args.timestamps else ()
    )
    if args.workspace:
        request = VideoEvidenceRequest(
            source_url=args.source_url,
            platform=args.platform,
            media_path=args.media_path,
            prompt=args.prompt,
            detail=detail,
            start=args.start,
            end=args.end,
            timestamps=timestamps,
            workspace=args.workspace,
            captions_path=args.captions_file,
            enable_stt=args.stt,
        )
        paths = write_workspace_bundle(request, args.workspace, duration_seconds=args.duration or None)
        summary = build_system_b_summary(args.workspace, paths)
        print(json.dumps({"workspace": args.workspace, "paths": paths, "summary": summary}, indent=2))
        return 0

    defaults = select_detail_defaults(detail, focused=focused)
    budget = frame_budget(args.duration, detail, focused=focused)
    manifest = VideoEvidenceManifest(
        source_url=args.source_url,
        platform=args.platform,
        detail=detail,
        warnings=[] if args.duration else ["duration_unknown: frame budget is provisional"],
        metadata={"planning_defaults": defaults, "planned_frame_budget": budget, "prompt": args.prompt},
    )
    if args.manifest:
        manifest.write_json(args.manifest)
    print(json.dumps(manifest.to_dict(), indent=2))
    return 0


def _run_invoke(args: argparse.Namespace) -> int:
    import tempfile

    from .invoke import run_invocation

    workspace = args.workspace or tempfile.mkdtemp(prefix="hermes-video-watch-")
    result = run_invocation(
        args.text,
        workspace,
        default_detail=normalize_detail_mode(args.detail) if args.detail else None,
        duration_seconds=args.duration or None,
    )
    print(json.dumps(result, indent=2))
    return 0


def _run_doctor(args: argparse.Namespace) -> int:
    report = dependency_report()
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ok" else 1


def _run_canary(args: argparse.Namespace) -> int:
    from .canary import run_canaries, write_report

    report = run_canaries(live_url=args.live_url)
    if args.report:
        write_report(report, args.report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ok" else 1


def _legacy_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Plan a Hermes Video evidence pass.")
    _add_watch_args(parser)
    return _run_watch(parser.parse_args(argv))


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] not in {"watch", "invoke", "doctor", "canary", "help", "-h", "--help"}:
        return _legacy_main(argv)

    parser = argparse.ArgumentParser(description="Hermes-native video evidence engine.")
    subparsers = parser.add_subparsers(dest="command")

    watch = subparsers.add_parser("watch", help="Prepare an evidence bundle for a video URL or file")
    _add_watch_args(watch)
    watch.set_defaults(func=_run_watch)

    invoke = subparsers.add_parser("invoke", help="Parse natural `/watch ...` text and run the evidence engine")
    invoke.add_argument("text", help="Natural request, e.g. '/watch https://youtu.be/ID what is this about?'")
    invoke.add_argument("--workspace", help="Output workspace; a temp dir is created when omitted")
    invoke.add_argument("--detail", choices=_DETAIL_CHOICES, help="Override the detail mode inferred from the text")
    invoke.add_argument("--duration", type=float, default=0.0, help="Known duration for planning")
    invoke.add_argument("--json", action="store_true", help="Emit JSON output (default)")
    invoke.set_defaults(func=_run_invoke)

    doctor = subparsers.add_parser("doctor", help="Check video tooling dependencies")
    doctor.add_argument("--json", action="store_true", help="Emit JSON output")
    doctor.set_defaults(func=_run_doctor)

    canary = subparsers.add_parser("canary", help="Run deterministic offline evidence canaries")
    canary.add_argument("--live-url", help="Optional live public URL; without it the live canary reports skipped_live_url")
    canary.add_argument("--report", help="Optional path base to write <report>.json and <report>.md")
    canary.add_argument("--json", action="store_true", help="Emit JSON output (default)")
    canary.set_defaults(func=_run_canary)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
