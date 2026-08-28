from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SAFE_HANDOFF_HEADERS = {"accept", "origin", "referer", "user-agent"}
SENSITIVE_HEADERS = {"authorization", "cookie", "proxy-authorization", "x-api-key"}


@dataclass(frozen=True)
class PageSpec:
    index: int
    url: str
    headers: dict[str, str]


@dataclass(frozen=True)
class ChapterSpec:
    chapter_id: str
    name: str
    source_url: str
    pages: tuple[PageSpec, ...]


@dataclass(frozen=True)
class SourceHandoff:
    project_id: str
    manga_url: str
    chapters: tuple[ChapterSpec, ...]

    @classmethod
    def load(cls, path: Path) -> "SourceHandoff":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema") != 1:
            raise ValueError("source handoff schema must be 1")
        if raw.get("provider") != "kotori":
            raise ValueError("source handoff provider must be kotori")
        project_id = _required_string(raw, "project_id")
        source = raw.get("source")
        if not isinstance(source, dict):
            raise ValueError("source must be an object")
        manga_url = _http_url(_required_string(source, "manga_url"), "source.manga_url")

        chapter_rows = raw.get("chapters")
        if not isinstance(chapter_rows, list) or not chapter_rows:
            raise ValueError("chapters must be a non-empty array")
        chapters: list[ChapterSpec] = []
        for chapter_row in chapter_rows:
            if not isinstance(chapter_row, dict):
                raise ValueError("each chapter must be an object")
            page_rows = chapter_row.get("pages")
            if chapter_row.get("pages_resolved") is not True or not isinstance(page_rows, list) or not page_rows:
                raise ValueError("MVP requires pages_resolved=true with at least one page")
            pages: list[PageSpec] = []
            seen_indexes: set[int] = set()
            for page_row in page_rows:
                if not isinstance(page_row, dict):
                    raise ValueError("each page must be an object")
                index = page_row.get("index")
                if not isinstance(index, int) or isinstance(index, bool) or index < 1 or index in seen_indexes:
                    raise ValueError("page indexes must be unique positive integers")
                seen_indexes.add(index)
                headers = _safe_headers(page_row.get("headers", {}))
                pages.append(PageSpec(index, _http_url(_required_string(page_row, "url"), "page.url"), headers))
            pages.sort(key=lambda page: page.index)
            chapters.append(
                ChapterSpec(
                    chapter_id=_required_string(chapter_row, "id"),
                    name=_required_string(chapter_row, "name"),
                    source_url=_http_url(_required_string(chapter_row, "source_url"), "chapter.source_url"),
                    pages=tuple(pages),
                )
            )
        return cls(project_id=project_id, manga_url=manga_url, chapters=tuple(chapters))


def _required_string(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _http_url(value: str, label: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{label} must be an absolute HTTP(S) URL")
    return value


def _safe_headers(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValueError("page.headers must be an object")
    result: dict[str, str] = {}
    for name, value in raw.items():
        normalized = str(name).strip().lower()
        if normalized in SENSITIVE_HEADERS:
            raise ValueError(f"sensitive header is forbidden in handoff: {name}")
        if normalized not in SAFE_HANDOFF_HEADERS:
            continue
        if isinstance(value, str) and value.strip():
            canonical = "-".join(part.capitalize() for part in normalized.split("-"))
            result[canonical] = value.strip()
    return result
