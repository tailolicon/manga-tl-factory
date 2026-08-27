from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from .core import slugify_source, utc_now, write_json


def submit(root: Path, source: str, *, source_language: str | None = None,
           target_language: str = "vi") -> dict[str, Any]:
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    kind = "url" if source.startswith(("http://", "https://")) else "archive"
    request = {
        "request_id": request_id,
        "source": {"kind": kind, "value": source},
        "source_language": source_language,
        "target_language": target_language,
        "created_at": utc_now(),
        "status": "pending_bootstrap",
    }
    write_json(root / "requests" / f"{request_id}.json", request)

    project_id = slugify_source(source)
    project_dir = root / "projects" / project_id
    if not project_dir.exists():
        template = root / "projects" / "_template"
        shutil.copytree(template, project_dir)
        project = {
            "project_id": project_id,
            "source": request["source"],
            "source_language": source_language,
            "target_language": target_language,
            "status": "new",
            "context_version": None,
            "pipeline_version": "1.0.0",
            "created_from_request": request_id,
        }
        write_json(project_dir / "project.json", project)
    request["project_id"] = project_id
    write_json(root / "requests" / f"{request_id}.json", request)
    return request
