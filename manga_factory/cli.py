from __future__ import annotations

import argparse
import json
from pathlib import Path

from .context import compile_context
from .intake import submit
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
        rows = []
        for path in sorted((root / "requests").glob("req-*.json")):
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

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
