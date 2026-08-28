# Standalone Test Mode

Standalone test mode exists so a ChatGPT worker can exercise the repository before an external coordinator such as Shiro is available. Production behavior remains unchanged.

## Two standalone modes

### A. Bootstrap-only mode

Use `python -m manga_factory test-envelope` for one selected `pending_bootstrap` request.

### B. Single-chapter test lane

`work/test_lanes/active.json` may point at one explicit `standalone_chapter_test` lane. Derive its envelope with:

```bash
python -m manga_factory chapter-test-envelope
```

The lane file on `main` is durable test coordinator state. Its `generation` is the test fencing token and the deterministic lease is `standalone-lane-<lane-id>-g<generation>`.

## Atomic claim

A worker must read the live lane, require `state` in `ready|partial` and `claim: null`, then atomically update that lane file on `main` using the blob SHA it just read. Claim only the declared `next_task`; do not invent child tasks.

Task artifacts remain on the task/test branch. The only direct-to-`main` exception is test-lane coordination state under `work/test_lanes/*.json`.

## Predeclared workflow transitions

A lane may include `workflow.predeclared: true` and ordered `workflow.steps[]`. A worker runs only the current step. On success, it may advance only to a next step that was already present on `main` before claim, incrementing `generation` by exactly one and stopping the current session.

## Page translation smoke

`page_translation_smoke` is a deliberately narrow test-only task. It exists to prove that one selected page can be fetched, visually inspected, translated to Vietnamese, and persisted as a `contracts/translation_page.schema.json` artifact before the production context/translation DAG is fully exercised.

Rules:

- Scope is exactly one page declared by `next_task.scope.page_index`.
- Reuse the existing Kotori source handoff; do not download the whole chapter again.
- Open only the page needed for the task.
- Translate the visible dialogue/text and write the Vietnamese translation artifact under `projects/<project>/translations/smoke/<chapter>/page-XXX.json` on the task branch.
- Use `context_version: "smoke:no-canonical-context"`; record ambiguity instead of inventing speaker/context facts.
- This artifact proves plumbing only. It does not modify canonical context, satisfy production `context_review`, publish, redraw, or claim the chapter fully translated.

## Runtime budget

The tool ceiling is 25 minutes:

- primary work target <=15 minutes;
- drain at minute 17;
- durable checkpoint/result by minute 20;
- substantive safety stop at minute 22;
- no new tool-heavy work at minute 24.

## Storage boundary

Raw image binaries must not be committed to normal Git history during this test phase. Temporary source pages may exist only in disposable worker runtime storage.
