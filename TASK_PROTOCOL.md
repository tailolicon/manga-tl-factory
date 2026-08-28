# Task Protocol

## Workers do not spawn workers

Workers may emit zero or more `task_proposals`. Only the external coordinator validates dependencies, deduplicates proposals and creates runnable production tasks.

The one exception is an explicit `standalone_chapter_test` lane declared on `main` under `work/test_lanes/`. In that mode the lane file, not the worker, predeclares the runnable test task. A worker may execute only the lane's existing `next_task`; it may not invent or enqueue a child task.

## Task fingerprint

A deterministic task should be identifiable from:

- project
- task type
- scope
- input hashes
- context version
- pipeline version

The reference library exposes deterministic fingerprint helpers so retries are idempotent.

## Dynamic splitting

A worker that finds a task too large may return a split proposal rather than running beyond its budget. Example:

```json
{
  "status": "split_requested",
  "task_proposals": [
    {"task_type": "translate_chunk", "scope": {"chapter": "20", "pages": [1, 8]}},
    {"task_type": "translate_chunk", "scope": {"chapter": "20", "pages": [9, 16]}}
  ]
}
```

The coordinator chooses whether to accept the split. In standalone chapter test mode, a split proposal remains inert unless a later `main` lane update explicitly predeclares one of those scopes as `next_task`.

## Dependency model

Tasks form a DAG. A task becomes runnable only when all required dependencies are accepted/completed at the required quality gate.

## Coordinator-less test modes

`STANDALONE_TEST.md` defines two explicit non-production authorities:

1. bootstrap-only testing derived from a `pending_bootstrap` request;
2. a single-chapter test lane under `work/test_lanes/`, whose `generation` acts as a test fencing token and whose `next_task` is the only runnable downstream test task.

These authorities are deliberately scoped and must never be treated as production coordinator leases.
