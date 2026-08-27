from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import read_json, sha256_json


def _load_json_dir(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for file in sorted(path.glob("*.json")):
        rows.append(read_json(file))
    return rows


def canonical_snapshot(project_dir: Path) -> dict[str, Any]:
    context_dir = project_dir / "context"
    snapshot = {
        "characters": _load_json_dir(context_dir / "characters"),
        "speech": _load_json_dir(context_dir / "speech"),
        "terminology": _load_json_dir(context_dir / "terminology"),
        "evidence": _load_json_dir(context_dir / "evidence"),
        "chapter_summaries": _load_json_dir(context_dir / "chapters"),
    }
    style_file = context_dir / "style" / "style.json"
    snapshot["style"] = read_json(style_file) if style_file.exists() else {}
    snapshot["context_version"] = "ctx:" + sha256_json(snapshot)[:24]
    return snapshot


def compile_context(project_dir: Path, *, chapter_id: str | None = None,
                    character_ids: list[str] | None = None,
                    term_ids: list[str] | None = None) -> dict[str, Any]:
    snapshot = canonical_snapshot(project_dir)
    wanted_chars = set(character_ids or [])
    wanted_terms = set(term_ids or [])

    chars = snapshot["characters"]
    speech = snapshot["speech"]
    terms = snapshot["terminology"]

    if wanted_chars:
        chars = [x for x in chars if x.get("id") in wanted_chars]
        speech = [x for x in speech if x.get("data", {}).get("character_id") in wanted_chars or x.get("id") in wanted_chars]
    if wanted_terms:
        terms = [x for x in terms if x.get("id") in wanted_terms]

    summaries = snapshot["chapter_summaries"]
    if chapter_id:
        summaries = [x for x in summaries if str(x.get("data", {}).get("chapter_id")) == str(chapter_id)]

    return {
        "context_version": snapshot["context_version"],
        "characters": chars,
        "speech": speech,
        "terminology": terms,
        "chapter_summaries": summaries,
        "style": snapshot["style"],
    }
