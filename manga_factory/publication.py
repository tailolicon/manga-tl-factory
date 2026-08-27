from __future__ import annotations

from typing import Any


def build_publication_manifest(*, series_id: str, chapter_id: str, pages: list[dict[str, Any]],
                               version: int = 1, title: str | None = None) -> dict[str, Any]:
    normalized = []
    for page in sorted(pages, key=lambda p: int(p["index"])):
        normalized.append({
            "index": int(page["index"]),
            "url": str(page["url"]),
            "width": int(page["width"]),
            "height": int(page["height"]),
            "sha256": str(page["sha256"]),
        })
    return {
        "series_id": series_id,
        "chapter_id": str(chapter_id),
        "title": title,
        "version": int(version),
        "pages": normalized,
    }
