# Stateless Worker Start

Use this file as the single entrypoint for a fresh ChatGPT worker session on `tailolicon/manga-tl-factory`.

Do not rely on chat history, private memory, previous worker reasoning, or stale assumptions. `main` is the source of truth.

## Objective

Make one useful, repository-backed unit of progress on the manga pipeline within a strict 25-minute tool/runtime ceiling.

For the current test phase, prefer the active single-chapter test lane when one exists. The first end-to-end success criterion is to produce one durable Vietnamese translation-page artifact before doing more infrastructure work.

## Mandatory startup hot path

Read only these first, in order:

1. `AGENTS.md`
2. `WORKER_PROTOCOL.md`
3. `TASK_PROTOCOL.md`
4. `STANDALONE_TEST.md`
5. `config/pipeline.json`
6. `README.md`
7. `work/test_lanes/active.json` if it exists

If an active lane exists, read only its referenced lane file and the minimum project/handoff/result evidence named by that lane. An active `standalone_chapter_test` lane is the explicit test authority described in `STANDALONE_TEST.md`.

Do not recursively read the whole repository before choosing work.

## Active chapter-lane rule

When `work/test_lanes/active.json` points to a lane:

1. Read the lane from current `main`.
2. Require `mode == "standalone_chapter_test"`.
3. If `state` is `ready` or `partial` and `claim` is null, derive the exact envelope described by `python -m manga_factory chapter-test-envelope`.
4. Atomically claim the lane by updating only the lane JSON on `main` with the blob SHA just read.
5. Use the lane `generation` as the standalone fencing token and `standalone-lane-<lane-id>-g<generation>` as the test lease.
6. Execute exactly the lane's `next_task`. Do not add or substitute story/content classification rules.
7. Write a formal test `worker_result`/handoff and any task artifact allowed by the envelope.
8. Release or advance the lane on `main` before ending the session.

`NO_COORDINATOR_LEASE` is not a valid blocker for a runnable test lane.

## Page-translation smoke task

`page_translation_smoke` is a test-only task used to prove one page can travel from source handoff to a durable Vietnamese translation artifact without waiting for the full production DAG.

For this task:

1. Use only the page index declared in `next_task.scope.page_index`.
2. Resolve that page from the existing Kotori handoff; do not re-fetch the whole chapter.
3. Download/open only that page in disposable runtime storage.
4. Inspect the page and translate its visible dialogue/text to Vietnamese.
5. Write a schema-compatible artifact under `projects/<project>/translations/smoke/<chapter>/page-XXX.json` on the task branch.
6. Use `context_version: "smoke:no-canonical-context"` and record uncertainty/speaker ambiguity in notes rather than inventing context.
7. Do not modify canonical context, publish, redraw, or claim production translation completion in this smoke task.

## Project identity and source reconciliation

Canonical project identity is about the series, not the website that supplied a chapter. A Kotori handoff may come from Manga18fx, MangaDistrict, or another source while belonging to the same canonical project.

Prefer exact `sources[]` binding, then `identity.series_key`, then `legacy_project_ids[]`. A legacy source-derived `project_id` is an import hint, not canonical identity.

## GitHub write-capability rule

If a connected GitHub capability exists, discover and use its write actions. Workers must not push directly to `main` except for coordinator state under `work/test_lanes/*.json`; normal artifacts go to the task/test branch.

## 25-minute hard budget

Treat 25 minutes as an external hard kill, not usable work time.

- Minute 0-3: startup + claim exactly one scope.
- Minute 3-15: primary work.
- Minute 15: mandatory durable checkpoint.
- Minute 17: enter `DRAINING`.
- Minute 20: result/handoff already recoverable.
- Minute 22: stop substantive work.
- Minute 24: no new tool-heavy operation.

Never start another page or pipeline stage because time remains.

## Acquisition rules

Use direct HTTP first, then safe source headers, then browser bootstrap only if direct HTTP fails. Do not commit raw page binaries to normal Git history.

## Completion rule

A successful session ends with one small, durable, reviewable unit of progress. For the current smoke lane, success means a real Vietnamese `translation_page` artifact for the declared page plus result/handoff, not another infrastructure-only change.
