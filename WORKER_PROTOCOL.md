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

The coordinator, not the worker, owns durable production task state.

## Runtime budget

A worker must use the runtime budget carried by its live task envelope rather than assuming an old fixed 15-minute payload window.

For the current 25-minute standalone chapter lane:

- continuous chapter work through about minute 21;
- drain begins at minute 21;
- result/handoff should be remotely recoverable by minute 23;
- substantive safety stop at minute 24.

Other production task types may use different coordinator-provided budgets. The worker must leave enough time for validation, persistence, result submission, and lease release, but should not reserve large idle margins that materially reduce useful work.

## Checkpoint policy

The atomic correctness boundary and the remote persistence cadence are separate concepts.

Atomic units include:

- translation: each completed page or stable scene block;
- context discovery: each evidence-backed candidate set;
- redraw: mask/cleanup/typeset stages or each completed page;
- QA: each completed page batch.

For translation, a completed page must never be represented as half-finished. However, workers should batch several complete page artifacts into one remote Git checkpoint when practical instead of forcing one commit/tool round-trip per page. Make rolling remote checkpoints often enough that an unexpected worker death loses only a small suffix, then force a final checkpoint during drain.

Checkpoint output must be valid and parseable even if the overall task is incomplete.

## Drain policy

When entering `DRAINING`:

1. Stop starting large new operations or a fresh chapter/page that cannot safely finish.
2. Finish only the smallest safe atomic unit already in progress.
3. Persist every completed but not-yet-remote page/artifact.
4. Validate the contiguous completed range and current artifacts.
5. Commit/push WIP on the task branch if Git is available.
6. Write a structured handoff whose resume point is the first uncompleted atomic unit.
7. Submit result/progress with the active fencing token.
8. Release the lease or standalone lane claim if still alive.

Unexpected death is handled by lease expiry. Cleanup is an optimization, never the safety mechanism.

## Stale worker protection

Every production result mutation must include the current coordinator fencing token. The coordinator rejects stale tokens. A worker whose lease expired may preserve a WIP branch, but it cannot publish/merge the stale result.

For an explicit `standalone_chapter_test` lane, the lane `generation` on `main` is the test-only fencing token. Claim/release uses compare-and-swap writes against the current lane blob SHA. A stale standalone claim must be cleared with a generation increment before another worker resumes. Standalone fencing tokens are never valid for production tasks.

## Git policy

Suggested branch naming:

`task/<task-id>/<fencing-token>`

Workers never merge their own production result into main. Review/integration is a separate task/role.

Standalone chapter testing has one narrow direct-main exception: `work/test_lanes/*.json` is coordinator state, so a worker may atomically claim/release/complete that state according to `STANDALONE_TEST.md`. All normal task artifacts still belong on the envelope's test/task branch unless the lane explicitly says otherwise.

## Standalone testing

`STANDALONE_TEST.md` defines the only coordinator-less exceptions:

1. the original deterministic bootstrap-only test envelope;
2. an explicit active single-chapter lane declared on `main`.

A worker in either mode must not block solely because no external coordinator or local worktree exists when the corresponding standalone authority is valid and an authorized GitHub connector is available.

If write access is unavailable, return an honest `partial` result rather than inventing commits, claims or fencing authority.
