from __future__ import annotations

import argparse
import json
from pathlib import Path

from .acquisition import fetch_source
from .context import compile_context
from .intake import submit
from .standalone import build_chapter_envelope, build_standalone_test_envelope
from .validate import validate_repo


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(prog="manga-factory")
    sub = parser.add_subparsers(dest="command", required=True)

    p_submit = sub.add_parser("submit", help="record a source URL/archive and initialize a project")
    p_submit.add_argument("source")
    p_submit.add_argument("--source-language", default=None)
    p_submit.add_argument("--target-language", default="vi")

    sub.add_parser("list-requests", help="list intake requests")
    sub.add_parser("validate", help="validate repository structure and pipeline references")

    p_test = sub.add_parser("test-envelope", help="derive a coordinator-less bootstrap envelope")
    p_test.add_argument("--request-id", default=None)

    p_chapter = sub.add_parser("chapter-envelope", help="derive the active production chapter envelope")
    p_chapter.add_argument("--lane-id", default=None)

    p_legacy = sub.add_parser("chapter-test-envelope", help=argparse.SUPPRESS)
    p_legacy.add_argument("--lane-id", default=None)

    p_fetch = sub.add_parser("fetch-source", help="download and verify a Kotori source handoff in disposable storage")
    p_fetch.add_argument("handoff", type=Path)
    p_fetch.add_argument("--result", type=Path, default=None)
    p_fetch.add_argument("--output-dir", type=Path, default=None)
    p_fetch.add_argument("--concurrency", type=int, default=6)
    p_fetch.add_argument("--timeout", type=float, default=30.0)
    p_fetch.add_argument("--retries", type=int, default=2)
    p_fetch.add_argument("--keep-temp", action="store_true")
    p_fetch.add_argument("--allow-private-hosts", action="store_true", help=argparse.SUPPRESS)

    p_context = sub.add_parser("compile-context", help="compile a deterministic canonical context bundle")
    p_context.add_argument("project_id")
    p_context.add_argument("--chapter")
    p_context.add_argument("--character", action="append", default=[])
    p_context.add_argument("--term", action="append", default=[])

    args = parser.parse_args()
    root = repo_root()

    if args.command == "submit":
        result = submit(root, args.source, source_language=args.source_language, target_language=args.target_language)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "list-requests":
        rows = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((root / "requests").glob("req-*.json"))]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if args.command == "test-envelope":
        try:
            envelope = build_standalone_test_envelope(root, request_id=args.request_id)
        except ValueError as exc:
            raise SystemExit(str(exc))
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return 0

    if args.command in {"chapter-envelope", "chapter-test-envelope"}:
        try:
            envelope = build_chapter_envelope(root, lane_id=args.lane_id)
        except ValueError as exc:
            raise SystemExit(str(exc))
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return 0

    if args.command == "fetch-source":
        try:
            result = fetch_source(
                args.handoff,
                result_path=args.result,
                output_root=args.output_dir,
                concurrency=args.concurrency,
                timeout=args.timeout,
                retries=args.retries,
                keep_temp=args.keep_temp,
                allow_private_hosts=args.allow_private_hosts,
            )
        except (OSError, ValueError) as exc:
            raise SystemExit(str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "success" else 1

    if args.command == "validate":
        errors = validate_repo(root)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("OK: repository contracts and pipeline references are valid")
        return 0

    if args.command == "compile-context":
        project_dir = root / "projects" / args.project_id
        if not project_dir.exists():
            raise SystemExit(f"unknown project: {args.project_id}")
        bundle = compile_context(project_dir, chapter_id=args.chapter,
                                 character_ids=args.character or None,
                                 term_ids=args.term or None)
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
