# Worker Protocol

## Execution lifecycle

A production worker receives a task envelope from the coordinator containing at least:

- `task_id`
- `task_type`
- `project_id`
- `lease_id`
- `fencing_token`
- `context_version` when applicable
- input artifact references/hashes
- allowed read/write paths
- runtime budget

Recommended state transitions:

```text
CLAIMED -> RUNNING -> DRAINING -> SUBMITTED
                   -> FAILED
```

The coordinator, not the worker, owns the durable task state.

## Runtime budget

Reference defaults:

- nominal work: <= 15 minutes
- start drain: 18 minutes
- safety stop: 22 minutes

The surrounding runtime may have a higher hard limit. The worker must not consume that entire limit.

## Checkpoint policy

Checkpoint after each meaningful atomic unit:

- translation: each completed page or stable scene block
- context discovery: each evidence-backed candidate set
- redraw: mask/cleanup/typeset stages or each completed page
- QA: each completed page batch

Checkpoint output must be valid and parseable even if incomplete.

## Drain policy

When entering `DRAINING`:

1. Stop starting large new operations.
2. Finish only the smallest safe atomic unit already in progress.
3. Validate current artifacts.
4. Commit/push WIP on the task branch if Git is available.
5. Write a structured handoff.
6. Submit result/progress with the active fencing token.
7. Release the lease if still alive.

Unexpected death is handled by lease expiry. Cleanup is an optimization, never the safety mechanism.

## Stale worker protection

Every result mutation must include the current fencing token. The coordinator rejects stale tokens. A worker whose lease expired may preserve a WIP branch, but it cannot publish/merge the stale result.

## Git policy

Suggested branch naming:

`task/<task-id>/<fencing-token>`

Workers never merge their own result into main. Review/integration is a separate task/role.
