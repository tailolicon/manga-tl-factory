# Stateless Worker Start

Use this file as the single entrypoint for a fresh ChatGPT worker session on `tailolicon/manga-tl-factory`.

Do not rely on chat history, private memory, previous worker reasoning, or stale assumptions. `main` is the source of truth.

## Objective

Make one useful, repository-backed unit of progress within the strict 25-minute tool/runtime ceiling. Optimize for useful work per session, not one-page task granularity and not an arbitrary page-count target.

For chapter translation, the worker owns the currently claimed chapter lane for the duration of the session. Keep translating that same chapter until it completes or the session reaches the drain window. A later worker resumes the unfinished suffix from the first uncompleted page.

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
4. Execute exactly `next_task` for that chapter; do not voluntarily split it just to hit a page-count target.
5. Treat each completed page as the atomic translation boundary, but batch remote persistence when practical instead of spending one GitHub commit/tool round-trip per page.
6. Release/complete/advance the lane on `main` before ending.

`NO_COORDINATOR_LEASE` is not a blocker for an active standalone test lane.

## Chapter-owned time-budgeted translation

`translation_chunk_test` is the current high-throughput test task. Despite the historical name, it is a resumable chapter task, not a fixed-size chunk target.

Its scope contains:

- `page_start`: first page belonging to the chapter work unit;
- `page_end`: last page allowed for this chapter work unit;
- `resume_from`: first not-yet-completed page;
- `soft_target_pages`: telemetry/planning hint only, never a completion or stop condition.

Rules:

1. Start at `resume_from` and process pages sequentially through at most `page_end`.
2. Keep working on the same chapter while there is enough time to finish another page safely before the drain threshold.
3. Never stop because `soft_target_pages` was reached or exceeded.
4. Produce one translation artifact per completed page under `projects/<project>/translations/smoke/<chapter>/page-XXX.json` on the task branch.
5. A page becomes resumable only after its complete artifact exists in worker state. Remote GitHub persistence may group several completed page artifacts into one checkpoint commit/tree update when the available tool supports batching.
6. Prefer a rolling remote checkpoint after a meaningful batch or before a risky/long operation; do not pay one remote commit round-trip after every page unless batching is unavailable.
7. If all pages through `page_end` finish, complete the chapter task. Do not claim another chapter or start another pipeline stage in the same worker session.
8. If time runs out first, return `partial` and set the lane's next `resume_from` to the first uncompleted page. The next worker claims the same chapter lane and resumes there.
9. Use `context_version: "smoke:no-canonical-context"` for this temporary test path and record uncertainty instead of inventing speaker/context facts.

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

Treat 25 minutes as an external kill. Optimize the useful translation window rather than reserving eight minutes by default.

- Minute 0-3: startup, claim, obtain/reuse chapter relay artifact.
- Minute 3-21: translate continuously on the claimed chapter, page by page.
- During work: make rolling remote checkpoints after meaningful batches when practical; a page-count soft target is never a reason to stop.
- Minute 21: enter `DRAINING`; do not start a new page unless it is clearly tiny and safe.
- Minute 21-23: finish only the current atomic page if safe, persist all completed page artifacts, validate contiguous progress, and write result/handoff.
- Minute 23: the result/handoff and resumable checkpoint should already be recoverable remotely.
- Minute 24: no substantive work and no new tool-heavy operation; only minimal claim release/final bookkeeping if still required.

If chapter completion happens before minute 21, complete and hand off early rather than claiming another chapter. Otherwise, use the available work window up to the drain threshold. `soft_target_pages` is informational only.

## Project identity

Canonical identity is series-based, not source-domain-based. Prefer exact `sources[]` binding, then `identity.series_key`, then `legacy_project_ids[]`.

## GitHub writes

Use authorized GitHub write capability when available. Only test-lane coordinator state under `work/test_lanes/*.json` may be written directly to `main`; normal task artifacts belong on the task/test branch.

When multiple completed page artifacts can be persisted in one Git tree/commit, prefer that over one commit per page. Correctness and recoverability still take priority over batching.

## Completion

A good session maximizes correctly completed pages in the claimed chapter while leaving a clean page-boundary checkpoint. Infrastructure changes are not the task unless the active lane explicitly assigns infrastructure work.
