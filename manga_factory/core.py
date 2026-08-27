from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def task_fingerprint(*, project_id: str, task_type: str, scope: dict[str, Any],
                     input_hashes: list[str] | None = None,
                     context_version: str | None = None,
                     pipeline_version: str = "1.0.0") -> str:
    payload = {
        "project_id": project_id,
        "task_type": task_type,
        "scope": scope,
        "input_hashes": sorted(input_hashes or []),
        "context_version": context_version,
        "pipeline_version": pipeline_version,
    }
    return "task:" + sha256_json(payload)[:24]


def slugify_source(source: str) -> str:
    parsed = urlparse(source)
    if parsed.scheme and parsed.netloc:
        seed = f"{parsed.netloc}{parsed.path}".strip("/")
    else:
        seed = Path(source).stem
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", seed).strip("-").lower()
    slug = slug[-64:] or "series"
    return slug


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
