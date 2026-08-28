# AGENTS.md

Repository instructions override model priors for this project.

## Source of truth

1. `config/pipeline.json`
2. `WORKER_PROTOCOL.md`
3. `CONTEXT_PROTOCOL.md`
4. `TASK_PROTOCOL.md`
5. `STANDALONE_TEST.md` for explicitly declared coordinator-less test authority
6. contract schemas under `contracts/`
7. the selected project's canonical context and manifest

## Core rules

- Never spawn another worker directly.
- Return structured `task_proposals`; the external coordinator alone creates/schedules production tasks.
- Never work without a valid coordinator-issued lease/fencing token in production.
- Never push directly to `main` from a normal worker.
- Translation/review workers must not directly modify canonical context.
- Every assertion promoted into canonical context needs provenance/evidence.
- Vision is the primary interpretation path for page meaning; OCR is supporting evidence.
- Use the task's pinned `context_version` and record it in every result.
- Checkpoint after meaningful atomic units, especially every completed page.
- Begin draining before the runtime hard limit; do not rely on final-minute cleanup.
- Submit uncertainty explicitly. Do not invent speaker identity, terminology or missing source text.
- Large binary images belong in object storage, not normal Git history.

## Standalone test exceptions

Before Shiro/another coordinator is installed, `STANDALONE_TEST.md` defines the only coordinator-less authorities:

1. the original bootstrap-only deterministic envelope for a selected `pending_bootstrap` request;
2. an explicit active `standalone_chapter_test` lane under `work/test_lanes/`.

For an active chapter lane, the lane state on current `main` is the test coordinator authority. Its `generation` is the test-only fencing token and its deterministic `lease_id` is valid only for the lane's predeclared `next_task`. The worker must atomically claim/release that lane using the current blob SHA.

The narrow direct-to-`main` exception applies only to coordinator state under `work/test_lanes/*.json`. Normal task artifacts remain on the task/test branch, and production behavior remains coordinator-only.

A worker in an authorized standalone mode must not block solely because no local worktree or external coordinator exists when an authorized GitHub connector is available. If write access is unavailable, return an honest `partial` result rather than inventing commits, claims or fencing authority.
