# Task Protocol

## Workers do not spawn workers

Workers may emit zero or more `task_proposals`. Only the external coordinator validates dependencies, deduplicates proposals and creates runnable tasks.

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

The coordinator chooses whether to accept the split.

## Dependency model

Tasks form a DAG. A task becomes runnable only when all required dependencies are accepted/completed at the required quality gate.
