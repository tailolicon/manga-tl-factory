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
    "WORKER_START.md",
    "config/pipeline.json",
    "contracts/source_manifest.schema.json",
    "contracts/task_proposal.schema.json",
    "contracts/worker_result.schema.json",
    "contracts/translation_page.schema.json",
    "contracts/test_lane.schema.json",
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


def _active_lane_path(root: Path) -> Path:
    pointer_path = root / "work" / "test_lanes" / "active.json"
    if not pointer_path.exists():
        raise ValueError("no active standalone chapter test lane")
    pointer = read_json(pointer_path)
    lane_path = pointer.get("lane_path")
    if not isinstance(lane_path, str) or not lane_path.strip():
        raise ValueError("active test lane pointer is missing lane_path")
    return root / lane_path


def build_standalone_chapter_test_envelope(root: Path, lane_id: str | None = None) -> dict[str, Any]:
    if lane_id is None:
        lane_path = _active_lane_path(root)
    else:
        lane_path = root / "work" / "test_lanes" / f"{lane_id}.json"
    if not lane_path.exists():
        raise ValueError(f"standalone chapter test lane not found: {lane_path.relative_to(root)}")

    lane = read_json(lane_path)
    if lane.get("mode") != "standalone_chapter_test":
        raise ValueError("test lane mode must be standalone_chapter_test")
    actual_lane_id = lane.get("lane_id")
    if not isinstance(actual_lane_id, str) or not actual_lane_id:
        raise ValueError("test lane is missing lane_id")
    if lane_id is not None and actual_lane_id != lane_id:
        raise ValueError(f"lane id mismatch: expected {lane_id}, found {actual_lane_id}")
    if lane.get("state") not in {"ready", "partial"}:
        terminal = lane.get("terminal_reason")
        suffix = f"; terminal_reason={terminal!r}" if terminal else ""
        raise ValueError(f"test lane is not runnable: state={lane.get('state')!r}{suffix}")
    if lane.get("claim") is not None:
        raise ValueError("test lane already has an active claim")

    project_id = lane.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise ValueError("test lane is missing project_id")
    chapter = lane.get("chapter")
    if not isinstance(chapter, dict) or not chapter.get("id"):
        raise ValueError("test lane is missing chapter identity")
    handoff = lane.get("source_handoff")
    if not isinstance(handoff, dict) or not handoff.get("path"):
        raise ValueError("test lane is missing source_handoff.path")
    next_task = lane.get("next_task")
    if not isinstance(next_task, dict) or not next_task.get("task_type"):
        raise ValueError("test lane has no runnable next_task")
    generation = lane.get("generation")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        raise ValueError("test lane generation must be a positive integer")

    task_type = str(next_task["task_type"])
    task_id = f"standalone-{actual_lane_id}-g{generation}-{task_type}"
    lease_id = f"standalone-lane-{actual_lane_id}-g{generation}"
    branch = f"test/{actual_lane_id}/{task_type}/g{generation}"
    lane_rel = str(lane_path.relative_to(root)).replace("\\", "/")

    allowed_write_paths = [
        f"work/results/{task_id}.json",
        f"work/handoffs/{task_id}.json",
    ]
    if task_type == "page_translation_smoke":
        allowed_write_paths.append(f"projects/{project_id}/translations/smoke/**")

    return {
        "execution_mode": "standalone_chapter_test",
        "task_id": task_id,
        "task_type": task_type,
        "goal": next_task.get("goal"),
        "scope": next_task.get("scope"),
        "project_id": project_id,
        "series_key": lane.get("series_key"),
        "chapter": chapter,
        "lease_id": lease_id,
        "fencing_token": generation,
        "context_version": None,
        "runtime_budget_minutes": 15,
        "drain_after_minutes": 17,
        "checkpoint_by_minutes": 20,
        "safety_stop_minutes": 22,
        "base_ref": "main",
        "task_branch": branch,
        "lane_path": lane_rel,
        "source_handoff": handoff,
        "acquisition_evidence": lane.get("acquisition_evidence", {}),
        "workflow": lane.get("workflow"),
        "input_artifacts": [
            {"kind": "test_lane", "path": lane_rel},
            {"kind": "project", "path": f"projects/{project_id}/project.json"},
            {"kind": "source_handoff", "path": handoff["path"], "blob_sha": handoff.get("blob_sha")},
        ],
        "allowed_read_paths": PROTOCOL_READ_PATHS
        + [
            lane_rel,
            f"projects/{project_id}/**",
            str(handoff["path"]),
            "work/imports/**/canonical_acquisition_validation.json",
        ],
        "allowed_write_paths": allowed_write_paths,
        "coordination_write_path": lane_rel,
        "standalone_constraints": {
            "single_chapter_only": True,
            "may_not_publish": True,
            "may_not_modify_canonical_context": True,
            "may_use_github_connector_without_local_worktree": True,
            "missing_local_git_is_not_a_blocker": True,
            "test_lease_only": True,
            "lane_state_on_main_is_coordinator_state": True,
            "raw_images_must_not_be_committed_to_git": True,
            "series_or_site_adult_metadata_must_not_preblock_pages": True,
            "actual_page_content_is_evaluated_only_when_opened": True,
        },
    }
