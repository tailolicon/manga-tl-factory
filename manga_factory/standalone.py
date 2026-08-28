from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import read_json


PROTOCOL_READ_PATHS = [
    "AGENTS.md",
    "WORKER_PROTOCOL.md",
    "TASK_PROTOCOL.md",
    "CONTEXT_PROTOCOL.md",
    "CHAPTER_PIPELINE.md",
    "WORKER_START.md",
    "config/pipeline.json",
    "contracts/source_manifest.schema.json",
    "contracts/task_proposal.schema.json",
    "contracts/worker_result.schema.json",
    "contracts/translation_page.schema.json",
    "contracts/chapter_lane.schema.json",
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
            f"standalone bootstrap requires exactly one pending_bootstrap request; found {len(pending)}. "
            "Pass --request-id explicitly."
        )

    request = pending[0]
    rid = request["request_id"]
    project_id = request["project_id"]
    return {
        "execution_mode": "standalone_bootstrap",
        "task_id": f"standalone-bootstrap-{rid}",
        "task_type": "bootstrap",
        "project_id": project_id,
        "request_id": rid,
        "lease_id": f"standalone-bootstrap-{rid}",
        "fencing_token": 1,
        "runtime_budget_minutes": 15,
        "drain_after_minutes": 18,
        "safety_stop_minutes": 22,
        "base_ref": "main",
        "task_branch": f"bootstrap/{rid}",
        "source": request["source"],
        "target_language": request.get("target_language", "vi"),
        "input_artifacts": [
            {"kind": "intake_request", "path": f"requests/{rid}.json"},
            {"kind": "project", "path": f"projects/{project_id}/project.json"},
        ],
        "allowed_read_paths": PROTOCOL_READ_PATHS + [f"requests/{rid}.json", f"projects/{project_id}/**"],
        "allowed_write_paths": [
            f"projects/{project_id}/source_manifest.json",
            f"projects/{project_id}/bootstrap/**",
            f"work/proposals/standalone-bootstrap-{rid}.json",
            f"work/results/standalone-bootstrap-{rid}.json",
            f"work/handoffs/standalone-bootstrap-{rid}.json",
        ],
    }


def _active_chapter_lane_path(root: Path) -> Path:
    pointer_path = root / "work" / "chapter_lanes" / "active.json"
    if not pointer_path.exists():
        raise ValueError("no active production chapter lane")
    pointer = read_json(pointer_path)
    lane_path = pointer.get("lane_path")
    if not isinstance(lane_path, str) or not lane_path.strip():
        raise ValueError("active chapter lane pointer is missing lane_path")
    return root / lane_path


def build_chapter_envelope(root: Path, lane_id: str | None = None) -> dict[str, Any]:
    lane_path = _active_chapter_lane_path(root) if lane_id is None else root / "work" / "chapter_lanes" / f"{lane_id}.json"
    if not lane_path.exists():
        raise ValueError(f"chapter lane not found: {lane_path.relative_to(root)}")

    lane = read_json(lane_path)
    if lane.get("mode") != "chapter_pipeline":
        raise ValueError("chapter lane mode must be chapter_pipeline")
    actual_lane_id = lane.get("lane_id")
    if not isinstance(actual_lane_id, str) or not actual_lane_id:
        raise ValueError("chapter lane is missing lane_id")
    if lane_id is not None and actual_lane_id != lane_id:
        raise ValueError(f"lane id mismatch: expected {lane_id}, found {actual_lane_id}")
    if lane.get("state") not in {"ready", "partial"}:
        raise ValueError(f"chapter lane is not runnable: state={lane.get('state')!r}")
    if lane.get("claim") is not None:
        raise ValueError("chapter lane already has an active claim")

    project_id = lane.get("project_id")
    chapter = lane.get("chapter")
    next_task = lane.get("next_task")
    generation = lane.get("generation")
    if not isinstance(project_id, str) or not project_id:
        raise ValueError("chapter lane is missing project_id")
    if not isinstance(chapter, dict) or not chapter.get("id"):
        raise ValueError("chapter lane is missing chapter identity")
    if not isinstance(next_task, dict) or next_task.get("task_type") != "localize_chapter":
        raise ValueError("chapter lane has no runnable localize_chapter task")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        raise ValueError("chapter lane generation must be a positive integer")

    chapter_id = str(chapter["id"])
    task_id = f"chapter-{actual_lane_id}-g{generation}"
    lease_id = f"chapter-lane-{actual_lane_id}-g{generation}"
    lane_rel = lane_path.relative_to(root).as_posix()
    handoff = lane.get("source_handoff") or {}
    last_result = lane.get("last_result") or {}
    checkpoint_base_commit = last_result.get("commit") if isinstance(last_result, dict) else None

    return {
        "execution_mode": "chapter_pipeline",
        "task_id": task_id,
        "task_type": "localize_chapter",
        "goal": next_task.get("goal"),
        "scope": next_task.get("scope"),
        "project_id": project_id,
        "series_key": lane.get("series_key"),
        "chapter": chapter,
        "phase": lane.get("phase"),
        "resume_page": lane.get("resume_page", 1),
        "page_count": lane.get("page_count"),
        "progress": lane.get("progress") or {},
        "accepted_inputs": lane.get("accepted_inputs") or {},
        "lease_id": lease_id,
        "fencing_token": generation,
        "runtime_budget_minutes": 25,
        "drain_after_minutes": 21,
        "checkpoint_by_minutes": 23,
        "safety_stop_minutes": 24,
        "base_ref": "main",
        "checkpoint_base_commit": checkpoint_base_commit,
        "task_branch": f"chapter/{actual_lane_id}/g{generation}",
        "lane_path": lane_rel,
        "source_handoff": handoff,
        "acquisition_evidence": lane.get("acquisition_evidence", {}),
        "relay": lane.get("relay"),
        "input_artifacts": [
            {"kind": "chapter_lane", "path": lane_rel},
            {"kind": "project", "path": f"projects/{project_id}/project.json"},
            *([{"kind": "source_handoff", "path": handoff.get("path"), "blob_sha": handoff.get("blob_sha")}] if handoff.get("path") else []),
        ],
        "allowed_read_paths": PROTOCOL_READ_PATHS + [
            lane_rel,
            f"projects/{project_id}/**",
            str(handoff.get("path") or ""),
            "work/imports/**/canonical_acquisition_validation.json",
            "work/relay_requests/*.json",
        ],
        "allowed_write_paths": [
            f"projects/{project_id}/chapters/{chapter_id}/translation/**",
            f"projects/{project_id}/chapters/{chapter_id}/rendered/**",
            f"projects/{project_id}/publication/{chapter_id}/**",
            f"work/results/{task_id}.json",
            f"work/handoffs/{task_id}.json",
        ],
        "coordination_write_path": lane_rel,
        "chapter_constraints": {
            "single_chapter_only": True,
            "generalist_worker": True,
            "phase_boundaries_are_handoffs": False,
            "worker_may_advance_phase": True,
            "worker_may_translate": True,
            "worker_may_correct_translation": True,
            "worker_may_redraw_and_typeset": True,
            "worker_may_qa": True,
            "worker_may_fix_qa_issues": True,
            "worker_may_publish_after_qa": True,
            "raw_source_images_must_not_be_committed": True,
            "final_localized_images_may_be_committed": True,
            "page_is_atomic_boundary": True,
            "soft_page_target_is_stop_condition": False,
            "remote_checkpoint_strategy": "adaptive_batched",
            "default_checkpoint_pages": 6,
            "min_checkpoint_pages": 4,
            "max_checkpoint_pages": 10,
            "max_uncommitted_minutes": 7,
            "force_flush_from_minute": 18,
            "parallel_blob_creation_when_supported": True,
            "one_tree_commit_ref_update_per_batch": True,
            "main_lane_updates_per_page": False,
            "inherit_previous_checkpoint_commit": True,
            "binary_persistence_strategy": "github_create_blob_base64_then_tree_commit",
            "binary_base64_is_transport_only": True,
            "rendered_progress_requires_remote_commit": True,
            "preferred_render_format": "webp",
            "target_render_bytes_per_page": 1048576,
        },
    }


# Compatibility alias for old callers. Active production work must use chapter-envelope.
def build_standalone_chapter_test_envelope(root: Path, lane_id: str | None = None) -> dict[str, Any]:
    return build_chapter_envelope(root, lane_id=lane_id)
