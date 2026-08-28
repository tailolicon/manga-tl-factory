from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
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


def normalize_page_url(value: str, manifest_path: Path) -> str:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https", "data"}:
        return value

    if value.startswith("/"):
        repo_path = value.lstrip("/")
    else:
        repo_path = (manifest_path.parent / value).resolve().relative_to(ROOT.resolve()).as_posix()
    return RAW_BASE + repo_path


def project_title(project: dict, project_id: str) -> str:
    identity = project.get("identity") or {}
    return (
        identity.get("canonical_title")
        or project.get("title")
        or project.get("name")
        or project_id
    )


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


def build_library() -> dict:
    series_rows: list[dict] = []
    chapter_count = 0

    if not PROJECTS.exists():
        return {"schema": 1, "generated_at": None, "chapter_count": 0, "series": []}

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

        chapter_rows: list[dict] = []
        for manifest_path in discover_manifests(project_dir / "publication"):
            manifest = load_json(manifest_path)
            pages = []
            for page in sorted(manifest.get("pages", []), key=lambda row: int(row.get("index", 0))):
                url = str(page.get("url") or "").strip()
                if not url:
                    continue
                pages.append(
                    {
                        "index": int(page.get("index", len(pages) + 1)),
                        "url": normalize_page_url(url, manifest_path),
                        "width": int(page.get("width", 0) or 0),
                        "height": int(page.get("height", 0) or 0),
                        "sha256": str(page.get("sha256") or ""),
                    }
                )

            if not pages:
                continue

            chapter_id = str(manifest["chapter_id"])
            chapter_rows.append(
                {
                    "id": chapter_id,
                    "title": manifest.get("title") or f"Chapter {chapter_id}",
                    "version": int(manifest.get("version", 1)),
                    "pages": pages,
                    "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
                }
            )

        if not chapter_rows:
            continue

        chapter_rows.sort(key=lambda row: natural_key(row["id"]))
        chapter_count += len(chapter_rows)

        identity = project.get("identity") or {}
        cover_url = project.get("cover_url") or identity.get("cover_url")
        if cover_url:
            cover_url = normalize_page_url(str(cover_url), project_path)
        else:
            cover_url = chapter_rows[0]["pages"][0]["url"]

        series_rows.append(
            {
                "id": project.get("project_id") or project_dir.name,
                "series_key": identity.get("series_key"),
                "title": project_title(project, project_dir.name),
                "target_language": project.get("target_language") or "vi",
                "status": project.get("status"),
                "cover_url": cover_url,
                "chapters": chapter_rows,
            }
        )

    series_rows.sort(key=lambda row: row["title"].casefold())
    return {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "chapter_count": chapter_count,
        "series": series_rows,
    }


def main() -> None:
    payload = build_library()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"site index: {len(payload['series'])} series / {payload['chapter_count']} chapters")


if __name__ == "__main__":
    main()
