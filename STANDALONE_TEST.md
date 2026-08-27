# Standalone Test Mode

Standalone test mode exists only so a ChatGPT worker can exercise the repository before an external coordinator such as Shiro is available.

It is an explicit exception to the production lease/worktree requirements. Production behavior remains unchanged.

## Scope

Standalone mode is deliberately narrow:

- only a `pending_bootstrap` intake request may be claimed;
- the worker may discover source metadata and page/chapter references that are accessible through its authorized web/browser tools;
- it may write a source manifest, bootstrap observations, a worker result, a handoff, and task proposals;
- it may not translate/redraw restricted content, publish, merge to `main`, or directly modify canonical context;
- proposed downstream tasks are inert until an external coordinator accepts them.

## Derive the envelope

When the repository is locally mounted:

```bash
python -m manga_factory test-envelope
# or, if more than one request is pending:
python -m manga_factory test-envelope --request-id req-xxxxxxxxxxxx
```

The derived envelope uses a deterministic standalone lease and fencing token (`1`). These values are valid only for standalone testing and must never be treated as production coordinator authority.

If no local checkout is available, a ChatGPT worker may read the selected pending request from GitHub and construct the exact same envelope according to `manga_factory/standalone.py`.

## GitHub connector fallback

A missing local Git worktree or shell DNS/network access is **not a blocker** in standalone mode when the worker has an authorized GitHub connector capable of reading/writing the repository.

Preferred order:

1. coordinator-provided local worktree;
2. authorized GitHub connector on a task branch;
3. read-only GitHub/web access, in which case perform safe analysis and return a `partial` result with inline artifacts/proposals rather than fabricating a push.

The worker must never claim it committed or pushed unless the write actually succeeded.

## Branch

When repository write access exists, create/use:

`test/<request-id>/bootstrap`

from the current `main`. Do not write directly to `main`.

## Completion

A standalone bootstrap run should aim to produce:

- `projects/<project-id>/source_manifest.json`
- optional `projects/<project-id>/bootstrap/*` observations
- `work/results/<task-id>.json`
- zero or more `work/proposals/<...>.json` / structured task proposals

If source acquisition is unavailable, return `partial` with the metadata/evidence that could be established and a clear warning. Do not mark the whole worker blocked merely because local Git is absent.
