from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import read_json


PROTOCOL_READ_PATHS = [
    "AGENTS.md",
    "WORKER_PROTOCOL.md",
    "TASK_PROTOCOL.md",
    "CONTEXT_PROTOCOL.md",
    "STANDALONE_TEST.md",
    "config/pipeline.json",
    "contracts/source_manifest.schema.json",
    "contracts/task_proposal.schema.json",
    "contracts/worker_result.schema.json",
]


def _pending_bootstrap_requests(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "requests").glob("req-*.json")):
        row = read_json(path)
        if row.get("status") == "pending_bootstrap":
            rows.append(row)
    return rows


def build_standalone_test_envelope(root: Path, request_id: str | None = None) -> dict[str, Any]:
    pending = _pending_bootstrap_requests(root)
    if request_id is not None:
        pending = [row for row in pending if row.get("request_id") == request_id]
        if not pending:
            raise ValueError(f"pending bootstrap request not found: {request_id}")
    elif len(pending) != 1:
        raise ValueError(
            f"standalone test mode requires exactly one pending_bootstrap request; found {len(pending)}. "
            "Pass --request-id explicitly."
        )

    request = pending[0]
    rid = request["request_id"]
    project_id = request["project_id"]
    task_id = f"standalone-bootstrap-{rid}"
    branch = f"test/{rid}/bootstrap"

    return {
        "execution_mode": "standalone_test",
        "task_id": task_id,
        "task_type": "bootstrap",
        "project_id": project_id,
        "request_id": rid,
        "lease_id": f"standalone-test-{rid}",
        "fencing_token": 1,
        "context_version": None,
        "runtime_budget_minutes": 15,
        "drain_after_minutes": 18,
        "safety_stop_minutes": 22,
        "base_ref": "main",
        "task_branch": branch,
        "source": request["source"],
        "target_language": request.get("target_language", "vi"),
        "input_artifacts": [
            {"kind": "intake_request", "path": f"requests/{rid}.json"},
            {"kind": "project", "path": f"projects/{project_id}/project.json"},
        ],
        "allowed_read_paths": PROTOCOL_READ_PATHS
        + [
            f"requests/{rid}.json",
            f"projects/{project_id}/**",
        ],
        "allowed_write_paths": [
            f"projects/{project_id}/source_manifest.json",
            f"projects/{project_id}/bootstrap/**",
            f"work/proposals/{task_id}.json",
            f"work/results/{task_id}.json",
            f"work/handoffs/{task_id}.json",
        ],
        "standalone_constraints": {
            "bootstrap_only": True,
            "may_not_publish": True,
            "may_not_modify_canonical_context": True,
            "may_use_github_connector_without_local_worktree": True,
            "missing_local_git_is_not_a_blocker": True,
        },
    }
