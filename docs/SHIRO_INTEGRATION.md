# Shiro Integration Contract

Shiro remains a separate project.

For this repository Shiro needs only a generic campaign/task interface capable of:

- opening this repo/project
- reading `config/pipeline.json`
- creating a bootstrap task for a submitted request
- supplying task envelopes with lease/fencing information
- accepting structured `worker_result` and `task_proposal` documents
- scheduling accepted proposals when DAG dependencies are satisfied
- preserving checkpoint branches/results across worker replacement
- rejecting stale fencing tokens

The manga repo must not import Shiro internals.

## Suggested worker envelope

```json
{
  "task_id": "...",
  "task_type": "translate_chunk",
  "project_id": "...",
  "lease_id": "...",
  "fencing_token": 42,
  "context_version": "ctx:...",
  "scope": {"chapter": "12", "pages": [8, 12]},
  "runtime": {"work_minutes": 15, "drain_at_minutes": 18, "safety_stop_minutes": 22}
}
```
