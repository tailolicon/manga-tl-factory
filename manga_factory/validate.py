from __future__ import annotations

import json
from pathlib import Path

REQUIRED_FILES = [
    "AGENTS.md", "WORKER_PROTOCOL.md", "CONTEXT_PROTOCOL.md", "TASK_PROTOCOL.md",
    "STANDALONE_TEST.md", "WORKER_START.md",
    "config/pipeline.json", "config/quality.json", "config/roles.json",
    "contracts/intake_request.schema.json", "contracts/task_proposal.schema.json",
    "contracts/worker_result.schema.json", "contracts/publication_manifest.schema.json",
    "contracts/source_handoff.schema.json", "contracts/test_lane.schema.json",
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

    active_pointer = root / "work" / "test_lanes" / "active.json"
    if active_pointer.exists():
        try:
            pointer = json.loads(active_pointer.read_text(encoding="utf-8"))
            lane_rel = pointer.get("lane_path")
            if not isinstance(lane_rel, str) or not lane_rel:
                errors.append("active test lane pointer is missing lane_path")
            elif not (root / lane_rel).exists():
                errors.append(f"active test lane does not exist: {lane_rel}")
        except Exception as exc:
            errors.append(f"invalid json {active_pointer.relative_to(root)}: {exc}")
    return errors
