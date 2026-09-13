"""Command-line entry point: validate lesson configs and render them
to .mp4.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bosque.pipeline import render_lesson_file
from bosque.schema import load_lesson, load_lesson_library

REPO_ROOT = Path(__file__).resolve().parents[2]


def validate_one(path: str) -> int:
    try:
        lesson = load_lesson(path)
    except Exception as exc:
        print(f"INVALID  {path}\n  {exc}", file=sys.stderr)
        return 1
    print(f"OK       {path}  ({lesson.lesson_id}, {len(lesson.vocab)} vocab)")
    return 0


def validate_all() -> int:
    try:
        lessons = load_lesson_library(REPO_ROOT / "lessons")
    except Exception as exc:
        print(f"INVALID  {exc}", file=sys.stderr)
        return 1
    for lesson_id, lesson in sorted(lessons.items()):
        print(f"OK       {lesson_id}  ({lesson.tier.value}, {len(lesson.vocab)} vocab)")
    print(f"\n{len(lessons)} lesson(s) validated.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="bosque")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_p = sub.add_parser("validate", help="Validate one or all lesson configs")
    validate_p.add_argument(
        "path", nargs="?", default=None, help="Path to a single lesson YAML file"
    )

    render_p = sub.add_parser("render", help="Render a lesson config to .mp4")
    render_p.add_argument("path", help="Path to a lesson YAML file")
    render_p.add_argument("--output-dir", default=None, help="Override output directory")

    args = parser.parse_args()

    if args.command == "validate":
        code = validate_one(args.path) if args.path else validate_all()
        sys.exit(code)
    elif args.command == "render":
        out_path = render_lesson_file(args.path, args.output_dir)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
