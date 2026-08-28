from __future__ import annotations

import json
from pathlib import Path

REQUIRED_FILES = [
    "AGENTS.md", "WORKER_PROTOCOL.md", "CONTEXT_PROTOCOL.md", "TASK_PROTOCOL.md",
    "config/pipeline.json", "config/quality.json", "config/roles.json",
    "contracts/intake_request.schema.json", "contracts/task_proposal.schema.json",
    "contracts/worker_result.schema.json", "contracts/publication_manifest.schema.json",
    "contracts/source_handoff.schema.json",
]


def validate_repo(root: Path) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f"missing required file: {rel}")
    for path in [root / "config" / "pipeline.json", root / "config" / "quality.json", root / "config" / "roles.json"]:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid json {path.relative_to(root)}: {exc}")
    if not errors:
        pipeline = json.loads((root / "config" / "pipeline.json").read_text(encoding="utf-8"))
        stages = pipeline.get("stages", {})
        for name, cfg in stages.items():
            for dep in cfg.get("requires", []):
                if dep not in stages:
                    errors.append(f"pipeline stage {name!r} references unknown dependency {dep!r}")
    return errors
