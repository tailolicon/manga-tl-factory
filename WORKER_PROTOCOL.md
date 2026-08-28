# Worker Protocol

## Execution lifecycle

Active chapter work uses a durable lane on `main` plus a short-lived worker branch.

Recommended lifecycle:

```text
CLAIMED -> RUNNING -> DRAINING -> SUBMITTED
                   -> FAILED
```

The worker owns one chapter for the session and may advance through multiple internal phases before draining.

## Production chapter ownership

For `mode: chapter_pipeline`, the task type is `localize_chapter`. Translation, redraw/typeset, QA and publish are not separate mandatory worker roles. They are resumable phases in one chapter lane.

If the current phase finishes and enough safe runtime remains, advance to the next phase immediately. Do not emit a handoff solely because a phase boundary was reached.

## Runtime budget

For the current 25-minute chapter lane:

- continuous useful chapter work through about minute 21;
- drain begins at minute 21;
- result/handoff should be remotely recoverable by minute 23;
- substantive safety stop at minute 24.

## Checkpoint policy

Atomic correctness boundaries and Git persistence cadence are separate.

- translation: completed page;
- redraw/typeset: completed localized page;
- QA: checked/fixed page;
- publish: complete manifest + referenced final assets.

Workers should batch several complete artifacts into one remote checkpoint when practical while keeping unexpected-loss exposure small.

## Drain policy

When entering `DRAINING`:

1. Stop starting large new operations.
2. Finish only the smallest safe atomic unit already in progress.
3. Persist all completed but not-yet-remote artifacts.
4. Record exact `phase` and first unfinished `resume_page`.
5. Validate the contiguous completed range.
6. Write result/handoff.
7. Clear the claim and increment lane generation for the next worker unless the chapter reached publish completion.

## Fencing

The live chapter lane `generation` is the fencing token for coordinator-less production chapter execution. A stale worker must not mutate lane state or promote publication outputs after a newer generation exists.

## Git policy

Suggested branch naming:

`chapter/<lane-id>/g<fencing-token>`

WIP artifacts live on that branch. Coordinator state under `work/chapter_lanes/*.json` may be updated directly on `main` with compare-and-swap semantics.

After QA passes, a worker holding the live fencing token may promote final localized assets and the publication manifest to `main`, then atomically mark the lane completed. Raw source images must never be promoted.

## Legacy test mode

Old `standalone_chapter_test` lanes and smoke artifacts are historical compatibility inputs only. Fresh workers must use `work/chapter_lanes/active.json` and `CHAPTER_PIPELINE.md` for active production work.
