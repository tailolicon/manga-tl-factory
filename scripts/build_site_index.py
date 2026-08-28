from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
TEST_LANES = ROOT / "work" / "test_lanes"
OUT = ROOT / "site" / "data" / "library.json"
RAW_BASE = "https://raw.githubusercontent.com/tailolicon/manga-tl-factory/main/"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def natural_key(value: str) -> tuple:
    parts = re.split(r"(\d+(?:\.\d+)?)", value)
    key: list[tuple[int, object]] = []
    for part in parts:
        if not part:
            continue
        try:
            key.append((0, float(part)))
        except ValueError:
            key.append((1, part.casefold()))
    return tuple(key)


def normalize_url(value: str, base_path: Path) -> str:
    value = value.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https", "data"}:
        return value
    if value.startswith("/"):
        repo_path = value.lstrip("/")
    else:
        repo_path = (base_path.parent / value).resolve().relative_to(ROOT.resolve()).as_posix()
    return RAW_BASE + repo_path


def project_title(project: dict, project_id: str) -> str:
    identity = project.get("identity") or {}
    return identity.get("canonical_title") or project.get("title") or project.get("name") or project_id


def discover_manifests(publication_dir: Path) -> list[Path]:
    if not publication_dir.exists():
        return []
    manifests: list[Path] = []
    for path in publication_dir.rglob("*.json"):
        try:
            payload = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if all(key in payload for key in ("series_id", "chapter_id", "version", "pages")):
            manifests.append(path)
    return manifests


def translated_chapters(project_id: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not TEST_LANES.exists():
        return rows

    for lane_path in TEST_LANES.glob("*.json"):
        if lane_path.name == "active.json":
            continue
        try:
            lane = load_json(lane_path)
        except (OSError, json.JSONDecodeError):
            continue
        if lane.get("project_id") != project_id:
            continue

        completed_step = None
        workflow = lane.get("workflow") or {}
        for step in workflow.get("steps") or []:
            if step.get("task_type") in {"translation_chunk_test", "translate_chunk"} and step.get("status") == "completed":
                completed_step = step
        if completed_step is None:
            continue

        scope = completed_step.get("scope") or {}
        start = int(scope.get("page_start") or 1)
        end = int(scope.get("page_end") or 0)
        page_count = end - start + 1 if end >= start else int((lane.get("acquisition_evidence") or {}).get("page_count") or 0)
        chapter = lane.get("chapter") or {}
        chapter_id = str(chapter.get("id") or "")
        if not chapter_id:
            continue

        last_result = lane.get("last_result") or {}
        rows[chapter_id] = {
            "id": chapter_id,
            "title": chapter.get("name") or f"Chapter {chapter_id}",
            "status": "translated",
            "page_count": page_count,
            "reader_available": False,
            "pages": [],
            "source_commit": last_result.get("commit"),
            "lane_path": lane_path.relative_to(ROOT).as_posix(),
        }
    return rows


def project_metadata(project: dict, project_path: Path) -> dict:
    identity = project.get("identity") or {}
    metadata = project.get("metadata") or {}
    cover = metadata.get("cover_url") or project.get("cover_url") or identity.get("cover_url") or ""
    return {
        "original_title": metadata.get("original_title") or identity.get("original_title"),
        "alternative_titles": metadata.get("alternative_titles") or identity.get("alternative_titles") or [],
        "authors": metadata.get("authors") or project.get("authors") or [],
        "artists": metadata.get("artists") or project.get("artists") or [],
        "publisher": metadata.get("publisher"),
        "type": metadata.get("type"),
        "year": metadata.get("year"),
        "publication_status": metadata.get("publication_status"),
        "total_chapters": metadata.get("total_chapters"),
        "genres": metadata.get("genres") or [],
        "content_rating": metadata.get("content_rating"),
        "synopsis": metadata.get("synopsis") or metadata.get("description"),
        "cover_url": normalize_url(str(cover), project_path) if cover else "",
        "metadata_sources": metadata.get("sources") or [],
    }


def build_library() -> dict:
    series_rows: list[dict] = []
    translated_count = 0
    published_count = 0

    if not PROJECTS.exists():
        return {
            "schema": 2,
            "generated_at": None,
            "chapter_count": 0,
            "translated_chapter_count": 0,
            "published_chapter_count": 0,
            "series": [],
        }

    for project_dir in sorted(PROJECTS.iterdir(), key=lambda p: p.name.casefold()):
        if not project_dir.is_dir() or project_dir.name.startswith("_"):
            continue
        project_path = project_dir / "project.json"
        if not project_path.exists():
            continue
        try:
            project = load_json(project_path)
        except (OSError, json.JSONDecodeError):
            continue

        project_id = str(project.get("project_id") or project_dir.name)
        chapters = translated_chapters(project_id)

        for manifest_path in discover_manifests(project_dir / "publication"):
            manifest = load_json(manifest_path)
            pages = []
            for page in sorted(manifest.get("pages", []), key=lambda row: int(row.get("index", 0))):
                url = normalize_url(str(page.get("url") or ""), manifest_path)
                if not url:
                    continue
                pages.append({
                    "index": int(page.get("index", len(pages) + 1)),
                    "url": url,
                    "width": int(page.get("width", 0) or 0),
                    "height": int(page.get("height", 0) or 0),
                    "sha256": str(page.get("sha256") or ""),
                })
            if not pages:
                continue
            chapter_id = str(manifest["chapter_id"])
            previous = chapters.get(chapter_id) or {}
            chapters[chapter_id] = {
                "id": chapter_id,
                "title": manifest.get("title") or previous.get("title") or f"Chapter {chapter_id}",
                "status": "published",
                "page_count": len(pages),
                "reader_available": True,
                "version": int(manifest.get("version", 1)),
                "pages": pages,
                "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
                "source_commit": previous.get("source_commit"),
            }

        chapter_rows = list(chapters.values())
        if not chapter_rows:
            continue
        chapter_rows.sort(key=lambda row: natural_key(str(row["id"])))

        translated_here = sum(1 for row in chapter_rows if row.get("status") in {"translated", "published"})
        published_here = sum(1 for row in chapter_rows if row.get("status") == "published")
        translated_count += translated_here
        published_count += published_here

        identity = project.get("identity") or {}
        meta = project_metadata(project, project_path)
        if not meta["cover_url"]:
            first_published = next((c for c in chapter_rows if c.get("pages")), None)
            if first_published:
                meta["cover_url"] = first_published["pages"][0]["url"]

        series_rows.append({
            "id": project_id,
            "series_key": identity.get("series_key"),
            "title": project_title(project, project_dir.name),
            "source_language": project.get("source_language"),
            "target_language": project.get("target_language") or "vi",
            "status": project.get("status"),
            "sources": project.get("sources") or ([project["source"]] if project.get("source") else []),
            "translated_chapters": translated_here,
            "published_chapters": published_here,
            "chapters": chapter_rows,
            **meta,
        })

    series_rows.sort(key=lambda row: row["title"].casefold())
    return {
        "schema": 2,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "chapter_count": translated_count,
        "translated_chapter_count": translated_count,
        "published_chapter_count": published_count,
        "series": series_rows,
    }


def main() -> None:
    payload = build_library()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"site index: {len(payload['series'])} series / "
        f"{payload['translated_chapter_count']} translated / "
        f"{payload['published_chapter_count']} published"
    )


if __name__ == "__main__":
    main()
