# Standalone Test Mode

Standalone test mode exists so a ChatGPT worker can exercise the repository before an external coordinator such as Shiro is available. Production behavior remains unchanged unless the production coordinator adopts the same chapter-owned scheduling policy.

## Two standalone modes

### A. Bootstrap-only mode

Use `python -m manga_factory test-envelope` for one selected `pending_bootstrap` request.

### B. Single-chapter test lane

`work/test_lanes/active.json` may point at one explicit `standalone_chapter_test` lane. Derive its envelope with:

```bash
python -m manga_factory chapter-test-envelope
```

The lane file on `main` is durable test coordinator state. Its `generation` is the test fencing token and the deterministic lease is `standalone-lane-<lane-id>-g<generation>`.

A chapter lane is the ownership unit for a worker session. A worker resumes at the lane's first unfinished page and keeps working on that same chapter until the chapter finishes or the session enters drain. Do not voluntarily stop because a soft page-count target was reached.

## Atomic claim

A worker must read the live lane, require `state` in `ready|partial` and `claim: null`, then atomically update that lane file on `main` using the blob SHA it just read. Claim only the declared `next_task`; do not invent child tasks.

Task artifacts remain on the task/test branch. The only direct-to-`main` exception is test-lane coordination state under `work/test_lanes/*.json`.

## Predeclared workflow transitions

A lane may include `workflow.predeclared: true` and ordered `workflow.steps[]`. A worker runs only the current step. On success, it may advance only to a next step that was already present on `main` before claim, incrementing `generation` by exactly one and stopping the current session.

## Lane completion is not pipeline completion

`state: "completed"` on a standalone lane means only that the lane exhausted its predeclared test steps. It must never be interpreted as proof that the production chapter DAG reached `publish`.

If a completed standalone lane stops before the terminal production stage, record a `pipeline_handoff` that states:

- the test lane is complete;
- the production pipeline is not complete;
- which test stage completed;
- the closest production equivalent when one exists;
- the next production stage and remaining production stages;
- whether an external coordinator is required to materialize downstream tasks.

Workers must not turn that handoff into an unpredeclared child task themselves. The production coordinator owns dependency checks and downstream scheduling.

## Page translation smoke

`page_translation_smoke` is a deliberately narrow test-only task. It exists to prove that one selected page can be fetched, visually inspected, translated to Vietnamese, and persisted as a `contracts/translation_page.schema.json` artifact before the production context/translation DAG is fully exercised.

Rules:

- Scope is exactly one page declared by `next_task.scope.page_index`.
- Reuse the existing Kotori source handoff; do not download the whole chapter again.
- Open only the page needed for the task.
- Translate the visible dialogue/text and write the Vietnamese translation artifact under `projects/<project>/translations/smoke/<chapter>/page-XXX.json` on the task branch.
- Use `context_version: "smoke:no-canonical-context"`; record ambiguity instead of inventing speaker/context facts.
- This artifact proves plumbing only. It does not modify canonical context, satisfy production `context_review`, publish, redraw, or claim the chapter fully translated.

## Chapter translation chunk test

`translation_chunk_test` is chapter-owned and resumable. Its `page_start`/`page_end` describe the allowed chapter range and `resume_from` is the first unfinished page. `soft_target_pages` is telemetry only.

- Translate sequentially from `resume_from`.
- Continue until the chapter finishes or minute 21 drain begins.
- Each page is an atomic correctness boundary.
- Remote persistence may batch multiple complete page artifacts into one Git checkpoint/tree update when practical.
- Use rolling checkpoints during the work window so unexpected loss is bounded, then persist all outstanding completed pages during drain.
- On partial completion, hand off `resume_from = first_uncompleted_page`; the next worker claims the same chapter and continues.
- Do not claim another chapter in the same session.

A completed `translation_chunk_test` with `context_version: "smoke:no-canonical-context"` remains a smoke-test translation result. It is not equivalent to production `context_review + translate_chunk + translation_review`, and it cannot by itself satisfy downstream production gates.

## Runtime budget

The tool ceiling is 25 minutes:

- minute 0-3: startup/claim/relay acquisition;
- minute 3-21: continuous useful work on the claimed chapter;
- minute 21: enter drain;
- by minute 23: translation artifacts, result, and handoff should be remotely recoverable;
- minute 24: substantive safety stop; no new tool-heavy work.

This budget intentionally uses most of the available session for chapter work instead of reserving the old minute-17-to-25 idle margin.

## Storage boundary

Raw image binaries must not be committed to normal Git history during this test phase. Temporary source pages may exist only in disposable worker runtime storage.
