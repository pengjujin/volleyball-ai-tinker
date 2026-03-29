#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.schemas.common import RulesetVariant
from backend.app.services.local_analysis import run_local_analysis


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a local volleyball video and generate a static report site.",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--video-path",
        help="Absolute or relative path to the local video file.",
    )
    source_group.add_argument(
        "--youtube-url",
        help="YouTube URL to analyze directly with Gemini.",
    )
    parser.add_argument(
        "--ruleset",
        required=True,
        choices=[variant.value for variant in RulesetVariant],
        help="Ruleset variant for the match.",
    )
    parser.add_argument(
        "--title",
        default="",
        help="Optional display title for the report.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory where the static report site should be written.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    args = parse_args()

    result = run_local_analysis(
        video_path=Path(args.video_path) if args.video_path else None,
        youtube_url=args.youtube_url,
        ruleset_variant=RulesetVariant(args.ruleset),
        title=args.title or None,
        output_root=Path(args.output_dir),
    )

    print("")
    print("Local analysis complete.")
    print(f"Video source type: {result.video_source_type.value}")
    print(f"Video: {result.video_path or result.video_url}")
    print(f"Report: {result.report_path}")
    print(f"Report URL: {result.report_url}")
    print(f"Analysis JSON: {result.analysis_json_path}")
    print(f"Returned set events: {len(result.set_events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
