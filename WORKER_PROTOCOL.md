# Worker Protocol

## Execution lifecycle

Active chapter work uses a durable lane on `main` plus a short-lived worker branch.

Recommended lifecycle:

```text
CLAIMED -> RUNNING -> DRAINING -> SUBMITTED
                   -> FAILED
```

The worker owns one chapter for the session and may perform every localization function needed to advance it.

## Production chapter ownership

For `mode: chapter_pipeline`, the task type is `localize_chapter`.

Translation, translation correction, redraw, typesetting, QA, fixing and publish are not separate mandatory worker roles. They are capabilities of the same generalist chapter worker. Internal phase names are resumable progress markers only.

If a phase finishes and enough safe runtime remains, advance immediately. Never emit a handoff solely because a role or phase boundary was crossed.

## Runtime budget

For the 25-minute chapter session:

- minute 0-2: startup/claim/checkpoint inheritance/relay;
- minute 2-18: continuous chapter work;
- minute 18-21: continue useful work while keeping pending durable backlog bounded;
- minute 21: drain begins;
- result/handoff should be recoverable by minute 23;
- substantive stop at minute 24.

There is no page-count stop condition.

## Checkpoint policy

Atomic correctness boundaries and Git persistence cadence are separate.

- translation: completed page;
- redraw/typeset: locally completed + visually accepted page queued for persistence, then durable once remotely committed;
- QA: checked/fixed page backed by the remotely committed asset;
- publish: complete manifest + referenced final assets.

### Default persistence cadence

Do not commit one page at a time in steady state.

Default batch target: **6 completed pages**.

Adaptive range: roughly **4-10 pages**, depending on page size, connector latency and remaining runtime.

Force a checkpoint after about **7 minutes without a durable checkpoint**, at phase completion, when pending payload becomes risky, around minute 18-19 if completed work is still local, or at drain.

A normal N-page checkpoint should use:

`N create_blob operations -> 1 create_tree -> 1 create_commit -> 1 update_ref`

If the tool runner supports safe concurrency for independent `create_blob` calls, issue those calls concurrently/parallel. Do not serialize unnecessary branch/tree/ref round-trips between pages.

Do not update `main` lane progress per page or per normal rolling checkpoint. Main coordinator writes are normally claim and final release/handoff or publish completion only.

### Binary assets through the GitHub connector

Do not treat absence of direct local-file upload as a blocker if Git blob/tree/ref writes are available.

For each queued rendered image:

1. optimize final asset when practical (prefer WebP/JPEG; preserve readability/fidelity);
2. target around <= 1 MiB/page when practical, never at the cost of unreadable text or visibly damaged artwork;
3. base64-encode raw bytes locally;
4. create a Git blob with `encoding: base64`;
5. collect blob SHAs for the batch;
6. create one tree mapping all batch paths to those blob SHAs;
7. create one commit parented by current task-branch head;
8. update task branch ref once;
9. verify ref advancement before recording durable progress.

Base64 is transport only and must never be stored as repository content.

## Cross-generation branch continuity

A generation must inherit the previous generation's accumulated durable chapter artifacts.

When `last_result.commit` or another explicit durable checkpoint head exists, use it as the new generation branch base. Do not create a clean branch from `main` and reconstruct earlier rendered pages later.

## Drain policy

When entering `DRAINING`:

1. stop starting large new operations;
2. finish only the smallest safe atomic unit already in progress;
3. flush every completed local output, including pending binary blobs/tree commit;
4. record exact phase and first unfinished page;
5. validate contiguous durable progress against remote task branch;
6. write result/handoff;
7. clear claim and increment generation unless chapter reached publish completion.

## Fencing

Live chapter lane `generation` is the fencing token. A stale worker must not mutate lane state or publish after a newer generation exists.

## Git policy

Suggested branch naming:

`chapter/<lane-id>/g<fencing-token>`

WIP artifacts live on that branch. Coordinator state under `work/chapter_lanes/*.json` may be updated directly on `main` with compare-and-swap semantics.

Text artifacts may use normal connector writes. Binary rendered pages use `create_blob(base64) -> create_tree -> create_commit -> update_ref` when direct upload is unavailable.

After QA passes, the same worker holding the live fencing token may promote final localized assets and publication manifest to `main`, then mark the lane completed. Raw source images must never be promoted.

## Legacy test mode

Old `standalone_chapter_test` lanes and smoke artifacts are historical compatibility inputs only. Fresh workers must use `work/chapter_lanes/active.json` and `CHAPTER_PIPELINE.md` for active production work.
