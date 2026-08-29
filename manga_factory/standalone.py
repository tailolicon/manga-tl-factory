from __future__ import annotations

from datetime import datetime, timezone
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


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _claim_expired(claim: Any, now: datetime) -> bool:
    if not isinstance(claim, dict):
        return False
    expires = _parse_timestamp(claim.get("expires_at"))
    return expires is not None and expires <= now


def _common_lane_values(lane: dict[str, Any], lane_path: Path, root: Path) -> tuple[str, dict[str, Any], dict[str, Any], str, str]:
    project_id = lane.get("project_id")
    chapter = lane.get("chapter")
    next_task = lane.get("next_task")
    actual_lane_id = lane.get("lane_id")
    if not isinstance(actual_lane_id, str) or not actual_lane_id:
        raise ValueError("chapter lane is missing lane_id")
    if not isinstance(project_id, str) or not project_id:
        raise ValueError("chapter lane is missing project_id")
    if not isinstance(chapter, dict) or not chapter.get("id"):
        raise ValueError("chapter lane is missing chapter identity")
    if not isinstance(next_task, dict) or next_task.get("task_type") != "localize_chapter":
        raise ValueError("chapter lane has no runnable localize_chapter task")
    lane_rel = lane_path.relative_to(root).as_posix()
    return project_id, chapter, next_task, actual_lane_id, lane_rel


def _base_envelope(lane: dict[str, Any], lane_path: Path, root: Path) -> dict[str, Any]:
    project_id, chapter, next_task, actual_lane_id, lane_rel = _common_lane_values(lane, lane_path, root)
    chapter_id = str(chapter["id"])
    handoff = lane.get("source_handoff") or {}
    return {
        "execution_mode": "chapter_pipeline",
        "task_type": "localize_chapter",
        "goal": next_task.get("goal"),
        "project_id": project_id,
        "series_key": lane.get("series_key"),
        "chapter": chapter,
        "page_count": lane.get("page_count"),
        "progress": lane.get("progress") or {},
        "accepted_inputs": lane.get("accepted_inputs") or {},
        "runtime_budget_minutes": 25,
        "drain_after_minutes": 21,
        "checkpoint_by_minutes": 23,
        "safety_stop_minutes": 24,
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
            "work/results/*.json",
            "work/handoffs/*.json",
        ],
        "coordination_write_path": lane_rel,
        "chapter_constraints": {
            "single_chapter_only": True,
            "generalist_worker": True,
            "parallelism_is_by_page_range_not_role": True,
            "phase_boundaries_are_handoffs": False,
            "worker_may_advance_phase": True,
            "worker_may_translate": True,
            "worker_may_correct_translation": True,
            "worker_may_redraw_and_typeset": True,
            "worker_may_qa": True,
            "worker_may_fix_qa_issues": True,
            "worker_may_publish_after_dependencies": True,
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
            "binary_persistence_strategy": "github_create_blob_base64_then_tree_commit",
            "binary_base64_is_transport_only": True,
            "preferred_render_format": "webp",
            "publication_quality_resolution_required": True,
            "preview_resolution_is_not_final": True,
        },
        "_lane_id": actual_lane_id,
        "_chapter_id": chapter_id,
    }


def _select_parallel_work(lane: dict[str, Any]) -> dict[str, Any]:
    parallel = lane.get("parallel")
    if not isinstance(parallel, dict):
        raise ValueError("parallel chapter lane is missing parallel coordinator state")
    units = parallel.get("units")
    if not isinstance(units, list) or not units:
        raise ValueError("parallel chapter lane has no work units")

    now = datetime.now(timezone.utc)
    active_claims = 0
    for unit in units:
        if isinstance(unit, dict) and unit.get("state") == "claimed" and not _claim_expired(unit.get("claim"), now):
            active_claims += 1
    max_active = int(parallel.get("max_active_claims") or len(units))

    # Prefer released ready/partial units in page order.
    if active_claims < max_active:
        for unit in sorted((u for u in units if isinstance(u, dict)), key=lambda u: (int(u.get("page_start") or 0), str(u.get("id") or ""))):
            if unit.get("state") in {"ready", "partial"} and unit.get("claim") is None:
                return {"kind": "range", "unit": unit, "reclaim_expired": False}

        # Then allow stealing an expired claim without blocking other ranges.
        for unit in sorted((u for u in units if isinstance(u, dict)), key=lambda u: (int(u.get("page_start") or 0), str(u.get("id") or ""))):
            if unit.get("state") == "claimed" and _claim_expired(unit.get("claim"), now):
                return {"kind": "range", "unit": unit, "reclaim_expired": True}

    all_complete = all(isinstance(u, dict) and u.get("state") == "completed" for u in units)
    finalization = parallel.get("finalization") or {}
    if all_complete:
        fin_state = finalization.get("state")
        fin_claim = finalization.get("claim")
        if fin_state in {"ready", "partial"} and fin_claim is None:
            return {"kind": "finalize", "finalization": finalization, "reclaim_expired": False}
        if fin_state == "blocked":
            # Lane writers may leave it blocked until the first envelope observes all units complete.
            return {"kind": "finalize", "finalization": finalization, "reclaim_expired": False}
        if fin_state == "claimed" and _claim_expired(fin_claim, now):
            return {"kind": "finalize", "finalization": finalization, "reclaim_expired": True}

    raise ValueError(f"no claimable chapter range; active_claims={active_claims}/{max_active}")


def _build_parallel_chapter_envelope(lane: dict[str, Any], lane_path: Path, root: Path) -> dict[str, Any]:
    env = _base_envelope(lane, lane_path, root)
    actual_lane_id = env.pop("_lane_id")
    chapter_id = env.pop("_chapter_id")
    parallel = lane["parallel"]
    selected = _select_parallel_work(lane)
    base_commit = parallel.get("base_commit")
    lease_minutes = int(parallel.get("lease_minutes") or 35)

    if selected["kind"] == "range":
        unit = selected["unit"]
        unit_id = str(unit.get("id") or "")
        if not unit_id:
            raise ValueError("parallel unit is missing id")
        generation = int(unit.get("generation") or 1) + (1 if selected["reclaim_expired"] else 0)
        task_id = f"chapter-{actual_lane_id}-{unit_id}-g{generation}"
        checkpoint_commit = unit.get("checkpoint_commit") or base_commit
        page_start = int(unit.get("page_start") or 1)
        page_end = int(unit.get("page_end") or page_start)
        phase = unit.get("phase") or "translate"
        resume_page = int(unit.get("resume_page") or page_start)
        env.update({
            "task_id": task_id,
            "lease_id": f"chapter-range-{actual_lane_id}-{unit_id}-g{generation}",
            "fencing_token": generation,
            "coordination_epoch": lane.get("generation"),
            "scope": {"page_start": page_start, "page_end": page_end},
            "phase": phase,
            "resume_page": resume_page,
            "base_ref": checkpoint_commit or "main",
            "checkpoint_base_commit": checkpoint_commit,
            "task_branch": f"chapter/{actual_lane_id}/{unit_id}/g{generation}",
            "work_unit": {
                "kind": "page_range",
                "id": unit_id,
                "page_start": page_start,
                "page_end": page_end,
                "phase": phase,
                "resume_page": resume_page,
                "expected_generation": int(unit.get("generation") or 1),
                "claim_generation": generation,
                "reclaim_expired_claim": bool(selected["reclaim_expired"]),
                "lease_minutes": lease_minutes,
            },
        })
        env["allowed_write_paths"] = [
            f"projects/{env['project_id']}/chapters/{chapter_id}/translation/**",
            f"projects/{env['project_id']}/chapters/{chapter_id}/rendered/**",
            f"work/results/{task_id}.json",
            f"work/handoffs/{task_id}.json",
        ]
        env["chapter_constraints"].update({
            "global_chapter_claim_is_used": False,
            "worker_owns_only_claimed_page_range": True,
            "non_overlapping_range_writes_required": True,
            "range_completion_requires_qa": True,
            "range_result_must_list_final_blob_shas": True,
            "worker_may_claim_another_range_if_time_remains": True,
            "claim_another_range_min_remaining_minutes": 7,
            "range_claim_lease_minutes": lease_minutes,
            "expired_range_claims_are_reclaimable": True,
        })
        return env

    finalization = selected["finalization"]
    generation = int(finalization.get("generation") or 1) + (1 if selected["reclaim_expired"] else 0)
    task_id = f"chapter-{actual_lane_id}-finalize-g{generation}"
    env.update({
        "task_id": task_id,
        "lease_id": f"chapter-finalize-{actual_lane_id}-g{generation}",
        "fencing_token": generation,
        "coordination_epoch": lane.get("generation"),
        "scope": {"page_start": 1, "page_end": int(lane.get("page_count") or 1)},
        "phase": "publish",
        "resume_page": 1,
        "base_ref": "main",
        "checkpoint_base_commit": None,
        "task_branch": f"chapter/{actual_lane_id}/finalize/g{generation}",
        "work_unit": {
            "kind": "finalize",
            "id": "finalize",
            "expected_generation": int(finalization.get("generation") or 1),
            "claim_generation": generation,
            "reclaim_expired_claim": bool(selected["reclaim_expired"]),
            "lease_minutes": lease_minutes,
        },
    })
    env["allowed_write_paths"] = [
        f"projects/{env['project_id']}/chapters/{chapter_id}/rendered/**",
        f"projects/{env['project_id']}/publication/{chapter_id}/**",
        f"work/results/{task_id}.json",
        f"work/handoffs/{task_id}.json",
    ]
    env["chapter_constraints"].update({
        "global_chapter_claim_is_used": False,
        "finalizer_is_generalist_worker": True,
        "all_ranges_must_be_completed_before_publish": True,
        "finalizer_must_verify_exact_page_coverage": True,
        "finalizer_promotes_only_publication_outputs_to_main": True,
        "finalization_claim_lease_minutes": lease_minutes,
    })
    return env


def _build_single_claim_chapter_envelope(lane: dict[str, Any], lane_path: Path, root: Path) -> dict[str, Any]:
    env = _base_envelope(lane, lane_path, root)
    actual_lane_id = env.pop("_lane_id")
    chapter_id = env.pop("_chapter_id")
    generation = lane.get("generation")
    if lane.get("state") not in {"ready", "partial"}:
        raise ValueError(f"chapter lane is not runnable: state={lane.get('state')!r}")
    if lane.get("claim") is not None:
        raise ValueError("chapter lane already has an active claim")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        raise ValueError("chapter lane generation must be a positive integer")
    task_id = f"chapter-{actual_lane_id}-g{generation}"
    last_result = lane.get("last_result") or {}
    checkpoint_base_commit = last_result.get("commit") if isinstance(last_result, dict) else None
    env.update({
        "task_id": task_id,
        "lease_id": f"chapter-lane-{actual_lane_id}-g{generation}",
        "fencing_token": generation,
        "scope": (lane.get("next_task") or {}).get("scope"),
        "phase": lane.get("phase"),
        "resume_page": lane.get("resume_page", 1),
        "base_ref": checkpoint_base_commit or "main",
        "checkpoint_base_commit": checkpoint_base_commit,
        "task_branch": f"chapter/{actual_lane_id}/g{generation}",
        "work_unit": {"kind": "legacy_single_claim"},
    })
    env["allowed_write_paths"] = [
        f"projects/{env['project_id']}/chapters/{chapter_id}/translation/**",
        f"projects/{env['project_id']}/chapters/{chapter_id}/rendered/**",
        f"projects/{env['project_id']}/publication/{chapter_id}/**",
        f"work/results/{task_id}.json",
        f"work/handoffs/{task_id}.json",
    ]
    env["chapter_constraints"]["global_chapter_claim_is_used"] = True
    return env


def build_chapter_envelope(root: Path, lane_id: str | None = None) -> dict[str, Any]:
    lane_path = _active_chapter_lane_path(root) if lane_id is None else root / "work" / "chapter_lanes" / f"{lane_id}.json"
    if not lane_path.exists():
        raise ValueError(f"chapter lane not found: {lane_path.relative_to(root)}")
    lane = read_json(lane_path)
    if lane.get("mode") != "chapter_pipeline":
        raise ValueError("chapter lane mode must be chapter_pipeline")
    actual_lane_id = lane.get("lane_id")
    if lane_id is not None and actual_lane_id != lane_id:
        raise ValueError(f"lane id mismatch: expected {lane_id}, found {actual_lane_id}")
    if lane.get("state") in {"completed", "blocked"}:
        raise ValueError(f"chapter lane is not runnable: state={lane.get('state')!r}")

    if lane.get("coordination_mode") == "parallel_ranges":
        return _build_parallel_chapter_envelope(lane, lane_path, root)
    return _build_single_claim_chapter_envelope(lane, lane_path, root)


# Compatibility alias for old callers. Active production work must use chapter-envelope.
def build_standalone_chapter_test_envelope(root: Path, lane_id: str | None = None) -> dict[str, Any]:
    return build_chapter_envelope(root, lane_id=lane_id)
