# Stateless Worker Start

Use this file as the single entrypoint for a fresh ChatGPT worker session on `tailolicon/manga-tl-factory`.

Do not rely on chat history, private memory, previous worker reasoning, or stale assumptions. `main` is the source of truth.

## Objective

Make one useful, repository-backed unit of progress within the strict 25-minute tool/runtime ceiling. Optimize for useful work per session, not one-page task granularity.

For the current test phase, prefer the active `standalone_chapter_test` lane. The first success target is durable Vietnamese translation artifacts for as many assigned pages as can be completed safely before draining.

## Startup hot path

Read only:

1. `AGENTS.md`
2. `WORKER_PROTOCOL.md`
3. `TASK_PROTOCOL.md`
4. `STANDALONE_TEST.md`
5. `config/pipeline.json`
6. `work/test_lanes/active.json`
7. the referenced active lane
8. only the handoff/relay/task artifacts named by that lane

Do not recursively scan the repository.

## Claim rule

For a runnable lane (`state` is `ready` or `partial`, `claim` is null):

1. Derive `python -m manga_factory chapter-test-envelope` semantics.
2. Atomically claim the lane on `main` using the blob SHA just read.
3. Use lane `generation` as fencing token and `standalone-lane-<lane-id>-g<generation>` as lease.
4. Execute exactly `next_task`.
5. Checkpoint after every completed page.
6. Release/complete/advance the lane on `main` before ending.

`NO_COORDINATOR_LEASE` is not a blocker for an active standalone test lane.

## Time-budgeted translation chunk

`translation_chunk_test` is the current high-throughput test task.

Its scope contains:

- `page_start`: first page belonging to this work unit;
- `page_end`: last page allowed for this work unit;
- `resume_from`: first not-yet-completed page;
- `soft_target_pages`: planning hint only, not a hard cap.

Rules:

1. Start at `resume_from` and process pages sequentially through at most `page_end`.
2. Do **not** stop after one page merely because one page completed successfully.
3. Continue while useful work can safely finish before the drain threshold.
4. Persist one translation artifact per completed page under `projects/<project>/translations/smoke/<chapter>/page-XXX.json` on the task branch.
5. After every page, that page is a durable checkpoint. Never redo completed pages unless explicitly requested.
6. If all pages through `page_end` finish early, complete the task. Do not start another pipeline stage.
7. If time runs out first, return `partial` and set the lane's next `resume_from` to the first uncompleted page. The next worker resumes there.
8. Use `context_version: "smoke:no-canonical-context"` for this temporary test path and record uncertainty instead of inventing speaker/context facts.

## Chapter relay artifact

ChatGPT worker networking may not resolve every source image host even when GitHub Actions can. When the active lane contains `relay` metadata, prefer the relay artifact instead of retrying the origin repeatedly.

Relay procedure:

1. Read `relay.request_commit`, `relay.run_id` when present, and `relay.artifact_name`.
2. If `run_id` is absent, find the `Chapter relay` Actions run whose `head_sha` equals `request_commit`.
3. Require a successful run, then download the named artifact with the connected GitHub capability.
4. The artifact contains the entire selected chapter plus `relay_manifest.json`.
5. Verify page files against the manifest/fetch hashes where available.
6. Reuse that one chapter artifact for every page processed in the current worker session; do not download the chapter once per page.
7. Raw images remain ephemeral and must not be committed to normal Git history.

## 25-minute hard budget

Treat 25 minutes as an external kill.

- Minute 0-3: startup, claim, obtain/reuse chapter relay artifact.
- Minute 3-17: translate continuously, page by page.
- Minute 15: ensure durable progress already exists.
- Minute 17: enter `DRAINING`; finish only the current page if safe.
- Minute 20: result/handoff/lane checkpoint must already be recoverable.
- Minute 22: no substantive translation work.
- Minute 24: no new tool-heavy operation.

The expected useful payload is multiple pages per session. `soft_target_pages` defaults around 10, but actual output is determined by page density and remaining time.

## Project identity

Canonical identity is series-based, not source-domain-based. Prefer exact `sources[]` binding, then `identity.series_key`, then `legacy_project_ids[]`.

## GitHub writes

Use authorized GitHub write capability when available. Only test-lane coordinator state under `work/test_lanes/*.json` may be written directly to `main`; normal task artifacts belong on the task/test branch.

## Completion

A good session maximizes correctly completed assigned pages while leaving a clean page-boundary checkpoint. Infrastructure changes are not the task unless the active lane explicitly assigns infrastructure work.
