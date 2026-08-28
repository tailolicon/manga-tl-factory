# Standalone Test Mode

Standalone test mode exists only so a ChatGPT worker can exercise the repository before an external coordinator such as Shiro is available.

It is an explicit exception to the production lease/worktree requirements. Production behavior remains unchanged.

## Two standalone modes

### A. Bootstrap-only mode

The original standalone mode remains available for a `pending_bootstrap` request:

- discover source metadata and page/chapter references accessible through authorized tools;
- write source manifest/bootstrap observations, a worker result, a handoff, and task proposals;
- do not publish, merge to `main`, or directly modify canonical context;
- proposed downstream tasks remain inert unless a coordinator or an explicit chapter test lane accepts them.

Derive the envelope with:

```bash
python -m manga_factory test-envelope
# or
python -m manga_factory test-envelope --request-id req-xxxxxxxxxxxx
```

### B. Single-chapter test lane

`work/test_lanes/active.json` may point at one explicit `standalone_chapter_test` lane. This is the coordinator-less path for exercising one already-selected chapter beyond bootstrap without inventing a production coordinator.

Derive its envelope with:

```bash
python -m manga_factory chapter-test-envelope
# or
python -m manga_factory chapter-test-envelope --lane-id <lane-id>
```

The lane file on `main` is durable coordinator state for test mode only. Its `generation` is the standalone fencing token. The deterministic lease is:

```text
standalone-lane-<lane-id>-g<generation>
```

These values are valid only for that exact test lane generation and must never be treated as production coordinator authority.

## Atomic claim for a chapter lane

A fresh worker must read the active lane from current `main` and claim it before performing the lane task.

Claim procedure:

1. Read `work/test_lanes/active.json` and the referenced lane file from current `main`.
2. Require lane `state` to be `ready` or `partial` and `claim` to be null.
3. Derive the envelope from the current lane generation.
4. Update only that lane file on `main`, using the blob SHA just read, setting:
   - `state: "claimed"`;
   - `claim.lease_id` to the deterministic lease;
   - `claim.fencing_token` to the lane generation;
   - `claim.task_id` to the derived task id;
   - `claim.started_at` to the real current timestamp;
   - `claim.expires_at` no more than 30 minutes later.
5. If the compare-and-swap write fails because the blob changed, the claim failed. Re-read live state; do not continue under the stale generation.

The narrow direct-to-`main` exception applies only to `work/test_lanes/*.json` coordination state. Task artifacts still go to the task/test branch unless the lane explicitly permits another path.

A claim older than its `expires_at` is stale. A later worker may atomically clear it and increment `generation` before deriving a replacement envelope. Never reuse a stale generation.

## Predeclared workflow transitions

A chapter lane may include a `workflow` object with `predeclared: true` and an ordered `steps[]` list. This is the only coordinator-less mechanism that may authorize more than one atomic stage without a human or external coordinator updating `main` between workers.

Rules:

1. Every workflow step must be declared on `main` before the worker that would run it starts.
2. A worker may run only the current `next_task`; it may not append, invent, reorder, or broaden workflow steps.
3. When a step completes successfully and another predeclared step exists, the completing worker may atomically advance the lane on `main` by:
   - marking the current workflow step `completed` and recording its real result task id;
   - incrementing `generation` by exactly 1;
   - setting `state: "ready"`;
   - setting `claim: null`;
   - setting `next_task` to the already-predeclared next step;
   - retaining `last_result` for the completed generation.
4. The next worker must derive a new lease/fencing token from the incremented generation and claim normally.
5. A worker must stop instead of advancing when `content_boundary`, role rules, dependency checks, or the lane definition forbid the next stage.
6. A terminal lane must set `next_task: null` and should set `terminal_reason` so a later worker can distinguish a deliberate stop from a missing coordinator.

This transition mechanism is test orchestration only. It does not change `config/pipeline.json`, create production tasks, or grant authority outside the single lane.

## Chapter-lane completion

For the current lane task, the worker may write a formal `worker_result` and `handoff` using the test fencing token because the lane itself is the authority that issued it.

On successful completion:

1. Validate the result/handoff.
2. Commit/push the task artifacts to the envelope's test branch when possible.
3. Atomically update the lane on `main` with the same blob-SHA discipline:
   - advance to the next already-predeclared workflow step if the rules above allow it; otherwise set `state: "completed"`;
   - `claim: null`;
   - `last_result` containing the real branch, commit, result path, handoff path, task id and fencing token.
4. Do not invent a child task. A later task requires either a predeclared workflow transition already present on `main` or a real coordinator.

For partial progress, set lane `state: "partial"`, clear the claim, preserve `generation`, and record the durable checkpoint in `last_result`. The next worker resumes the same generation only if the previous claim was cleanly released; stale claims require a generation increment.

## Runtime budget

The surrounding tool limit is 25 minutes. Standalone chapter workers use:

- primary work target: <= 15 minutes;
- begin draining: minute 17;
- durable checkpoint/result by minute 20;
- substantive-work safety stop: minute 22;
- no new tool-heavy operation at minute 24.

Do not spend the last minutes discovering new scope.

## GitHub connector fallback

A missing local Git worktree or shell DNS/network access is **not a blocker** when the worker has an authorized GitHub connector capable of reading/writing the repository.

Preferred order:

1. coordinator-provided local worktree;
2. authorized GitHub connector on the envelope's task/test branch;
3. read-only GitHub/web access, in which case perform safe analysis and return `partial` rather than fabricating a push.

The worker must never claim it committed or pushed unless the write actually succeeded.

## Content and publication boundaries

Standalone authority does not override content-safety or role boundaries. It does not grant permission to translate/redraw restricted content, publish, or modify canonical context directly.

A lane may set `content_boundary.semantic_model_stages_allowed: false` and a `stop_after_task`. When present, a worker must not advance into semantic vision, translation, redraw, typesetting, or publication stages for that lane. The terminal stop is deliberate and should be recorded in `terminal_reason`; it is not a coordinator failure.

Large/raw page binaries must not be committed to normal Git history during this test phase.
