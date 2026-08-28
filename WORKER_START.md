# Stateless Worker Start

Use this file as the single entrypoint for a fresh ChatGPT worker session on `tailolicon/manga-tl-factory`.

Do not rely on chat history, private memory, previous worker reasoning, or stale assumptions. `main` is the source of truth.

## Objective

Make one useful, repository-backed unit of progress on the manga pipeline within a strict 25-minute tool/runtime ceiling.

For the current test phase, prefer the active single-chapter test lane when one exists. Do not add long-term object storage yet unless `main` explicitly says the test phase has advanced to that point.

## Mandatory startup hot path

Read only these first, in order:

1. `AGENTS.md`
2. `WORKER_PROTOCOL.md`
3. `TASK_PROTOCOL.md`
4. `STANDALONE_TEST.md`
5. `config/pipeline.json`
6. `README.md`
7. `work/test_lanes/active.json` if it exists

If an active lane exists, read only its referenced lane file and the minimum project/handoff/result evidence named by that lane. Do **not** fall back to coordinator-only production rules merely because no external lease service is present; an active `standalone_chapter_test` lane is itself the explicit test authority described in `STANDALONE_TEST.md`.

If no active lane exists, then inspect the selected project's `project.json` and only the minimum live files needed to find one runnable unit, such as an existing source handoff, source manifest, task/result/handoff, acquisition result, or chapter descriptor.

Do not recursively read the whole repository before choosing work.

## Active chapter-lane rule

When `work/test_lanes/active.json` points to a lane:

1. Read the lane from current `main`.
2. Require `mode == "standalone_chapter_test"`.
3. If `state` is `ready` or `partial` and `claim` is null, derive the exact envelope described by `python -m manga_factory chapter-test-envelope` (or construct the identical values from the lane when no local checkout exists).
4. Atomically claim the lane by updating only the lane JSON on `main` with the blob SHA just read, as specified in `STANDALONE_TEST.md`.
5. Use the lane `generation` as the standalone fencing token and `standalone-lane-<lane-id>-g<generation>` as the test lease.
6. Execute **exactly the lane's `next_task`**. Do not re-run earlier successful work unless the lane explicitly asks for revalidation.
7. Write a formal test `worker_result`/handoff using that test fencing token when the task completes.
8. Release or advance the lane state on `main` before ending the session.

An active runnable lane means `NO_COORDINATOR_LEASE` is **not a valid blocker** for that lane task. Production tasks outside the lane still require a real coordinator-issued lease.

If a claim is already live, do not duplicate the task. If it is past its recorded `expires_at`, follow the stale-claim recovery rule in `STANDALONE_TEST.md` and increment generation before retrying.

If the active lane is already `completed` with `next_task: null`, inspect `terminal_reason` and the predeclared workflow. Do not reopen the completed task. Report the terminal condition concisely unless a valid predeclared transition already exists on `main`.

## Predeclared workflow transition rule

A lane may declare `workflow.predeclared: true` with ordered `workflow.steps[]`.

After successfully completing the current step:

1. Mark only the current predeclared step completed and record its real result task id.
2. Check whether another workflow step was already present on `main` before this worker claimed the lane.
3. Check pipeline dependencies, role boundaries, and `content_boundary` before advancing.
4. If the next predeclared step is permitted, atomically increment `generation` by exactly 1, set `state: "ready"`, clear `claim`, set `next_task` to that existing step, retain `last_result`, and end the current worker. Do not run the next stage in the same 25-minute session.
5. If the next stage is forbidden or no predeclared step remains, set/retain `state: "completed"`, `claim: null`, `next_task: null`, and a specific `terminal_reason`.

Never append a new workflow step, invent a child task, or advance past a content boundary. The purpose of predeclared transitions is to avoid a human having to reopen the lane between safe atomic workers, not to weaken production task authority.

## Project identity and source reconciliation

Canonical project identity is about the series, not the website that supplied a chapter.

A Kotori handoff can come from Manga18fx, MangaDistrict, or another source while still belonging to the same canonical project. Do not treat a different source domain as a blocker by itself.

For current and legacy handoffs:

1. Read the handoff `series.title`, `source.source_id`, `source.source_name`, and `source.manga_url`.
2. Read candidate `projects/*/project.json` only as needed.
3. Prefer an exact source binding in a project's `sources[]`.
4. Otherwise match `project.identity.series_key` against a source-neutral normalized title key from `series.title`.
5. Treat `project.identity.legacy_project_ids[]` as accepted aliases for older source-derived Kotori `project_id` values.
6. If exactly one canonical project matches, continue the task under that canonical project's `project_id` even when the handoff's legacy `project_id` differs.
7. Block only when no project matches or more than one project matches ambiguously. Record an identity-review handoff instead of guessing.

Legacy schema-1 Kotori handoffs may contain a source-derived `project_id`; that value is an import hint, not authoritative canonical identity.

Do not download a chapter again merely to repair project identity when the existing handoff/acquisition evidence is already complete and source bindings are sufficient.

## GitHub write-capability rule

This repository is coordinated through GitHub. If a connected GitHub capability exists, discover and use its write actions rather than assuming GitHub is read-only.

Workers must not push directly to `main` except for the explicit coordinator-state exception under `work/test_lanes/*.json` in standalone chapter test mode. Normal task artifacts belong on the task/test branch.

If write capability is genuinely unavailable, do the maximum verifiable read-only work and return `partial`; never invent a commit, branch, lease, claim, or result.

## 25-minute hard budget

Treat 25 minutes as an external hard kill, not a usable work budget.

- Minute 0-3: startup, inspect active lane/live task, atomically claim exactly one atomic scope.
- Minute 3-15: primary work.
- Minute 15: first mandatory durable checkpoint. If no durable progress exists yet, reduce scope immediately.
- Minute 17: enter `DRAINING`; stop starting large operations, broad searches, full-series fetches, or multi-chapter work.
- Minute 20: second mandatory checkpoint; current result/handoff must already be parseable and recoverable.
- Minute 22: safety stop for substantive work. Only validation, commit/push, result/handoff writes, and lane release/transition may continue.
- Minute 24: no new tool-heavy operation. Finish only the smallest pending repository write if safe.

Never consume the last minutes trying to finish a large chapter or full pipeline stage.

## Scope rules

Choose exactly one of these, based on live state:

1. Execute the active lane's single `next_task`.
2. Verify/fetch one existing chapter source handoff when no active lane exists.
3. Resolve/fix one acquisition blocker for one chapter.
4. Validate one existing acquisition result/manifest.
5. Run one already-proposed downstream task whose dependencies are clearly satisfied and whose scope fits the budget.
6. If the live task is too large, checkpoint what is known and emit a split proposal rather than overrunning.

Do not process multiple chapters or multiple pipeline stages merely because time remains.

For acquisition testing, prefer the following strategy order:

1. direct HTTP from the source handoff;
2. source-required non-sensitive headers such as Referer/User-Agent;
3. browser/session bootstrap only if direct HTTP demonstrably fails;
4. if Android-specific runtime/session is still required, record that explicitly as a blocker instead of fabricating success.

Do not commit raw manga page binaries to normal Git history during this test phase. Temporary downloaded pages may exist only in the worker runtime and should be treated as disposable unless the live repo says otherwise.

## Checkpoint content

A checkpoint/result must be useful to the next stateless worker. Record at least:

- project/task/chapter scope;
- current status: `success`, `partial`, `failed`, or `split_requested`;
- exact inputs inspected;
- completed atomic units/pages;
- remaining work;
- blockers and HTTP/browser evidence when acquisition failed;
- branch/commit or durable artifact paths actually written;
- context version/fencing token when the live protocol requires them;
- next recommended smallest action;
- lane generation and terminal/transition reason when standalone chapter mode is active.

Never claim work that was not durably written or independently verifiable.

## Translation/content safety

Follow the live repository's content and role boundaries. Metadata/acquisition plumbing may proceed independently of translation eligibility. If a lane has `content_boundary.semantic_model_stages_allowed: false`, do not advance into semantic vision, translation, redraw, typesetting, or publication even if those stages appear later in `config/pipeline.json`.

If source pages contain content the active worker is not allowed to translate/redraw/reproduce, stop at the authorized technical boundary and record it as a deliberate terminal condition rather than a missing-coordinator error.

## Completion rule

A successful session ends with one small, durable, reviewable unit of progress and a handoff that another fresh worker can resume without chat history.

If a safe next workflow step was predeclared before the worker began, advance the lane to that next generation and stop. Otherwise complete the lane with a specific terminal reason.

Do not end with only an explanation when GitHub write access was available and the selected task required a repository write.
