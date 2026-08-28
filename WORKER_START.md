# Stateless Worker Start

Use this file as the single entrypoint for a fresh ChatGPT worker session on `tailolicon/manga-tl-factory`.

Do not rely on chat history, private memory, previous worker reasoning, or stale assumptions. `main` is the source of truth.

## Objective

Make one useful, repository-backed unit of progress on the manga pipeline within a strict 25-minute tool/runtime ceiling.

For the current test phase, prefer existing source-handoff/acquisition work for an already-known chapter before inventing broader infrastructure. Do not add long-term object storage yet unless `main` explicitly says the test phase has advanced to that point.

## Mandatory startup hot path

Read only these first, in order:

1. `AGENTS.md`
2. `WORKER_PROTOCOL.md`
3. `TASK_PROTOCOL.md`
4. `config/pipeline.json`
5. `README.md`
6. the selected project's `project.json`

Then inspect only the minimum live files needed to find one runnable unit, such as an existing source handoff, source manifest, task/result/handoff, acquisition result, or chapter descriptor.

Do not recursively read the whole repository before choosing work.

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

Workers must not push directly to `main` unless the live repository protocol explicitly grants a coordinator-less exception for that exact task class. Prefer a task/WIP branch and durable handoff/result artifacts.

If write capability is genuinely unavailable, do the maximum verifiable read-only work and return `partial`; never invent a commit, branch, lease, claim, or result.

## 25-minute hard budget

Treat 25 minutes as an external hard kill, not a usable work budget.

- Minute 0-3: startup, locate live project/task/chapter, choose exactly one atomic scope.
- Minute 3-15: primary work.
- Minute 15: first mandatory durable checkpoint. If no durable progress exists yet, reduce scope immediately.
- Minute 17: enter `DRAINING`; stop starting large operations, broad searches, full-series fetches, or multi-chapter work.
- Minute 20: second mandatory checkpoint; current result/handoff must already be parseable and recoverable.
- Minute 22: safety stop for substantive work. Only validation, commit/push, result/handoff writes, and concise final reporting may continue.
- Minute 24: no new tool-heavy operation. Finish only the smallest pending repository write if safe.

Never consume the last minutes trying to finish a large chapter or full pipeline stage.

## Scope rules

Choose exactly one of these, based on live state:

1. Verify/fetch one existing chapter source handoff.
2. Resolve/fix one acquisition blocker for one chapter.
3. Validate one existing acquisition result/manifest.
4. Run one already-proposed downstream task whose dependencies are clearly satisfied and whose scope fits the budget.
5. If the live task is too large, checkpoint what is known and emit a split proposal rather than overrunning.

Do not process multiple chapters merely because time remains.

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
- next recommended smallest action.

Never claim work that was not durably written or independently verifiable.

## Translation/content safety

Follow the live repository's content and role boundaries. Metadata/acquisition plumbing may proceed independently of translation eligibility. If source pages contain content the active worker is not allowed to translate/redraw/reproduce, stop at acquisition/metadata/technical verification and record the boundary clearly.

## Completion rule

A successful session ends with one small, durable, reviewable unit of progress and a handoff that another fresh worker can resume without chat history.

Do not end with only an explanation when GitHub write access was available and the selected task required a repository write.
