# Chapter Production Pipeline

This is the production execution contract for `manga-tl-factory`. It replaces the old smoke/test chapter flow for active work.

## One chapter, one generalist worker task

The coordinator exposes one task type: `localize_chapter`.

A worker claims one chapter and may perform every localization function needed by that chapter: translation, translation correction, redraw, typesetting, visual inspection, QA, fixes, and publication.

Internal phases are resumable state markers only:

```text
translate -> redraw_typeset -> qa -> publish -> done
```

They are **not separate worker roles** and are **not scheduling boundaries**. If a phase finishes and useful session time remains, the current worker immediately advances to the next phase.

## Phase rules

### translate

Inspect the source page directly, translate all reader-facing text, and verify the translation before marking the page complete. Store canonical page translation artifacts under:

`projects/<project>/chapters/<chapter>/translation/page-XXX.json`

Historical translation artifacts may be accepted as migration input when the lane explicitly pins their commit/path.

### redraw_typeset

For each page, use the source page plus accepted translation to remove/cover source text where required and typeset Vietnamese. The same worker performs redraw and typesetting.

Store final localized page images under:

`projects/<project>/chapters/<chapter>/rendered/page-XXX.<ext>`

Raw source images are ephemeral and must not be committed. Final localized/rendered pages are publication outputs and may be committed.

Before typesetting a page, correct an obvious translation mistake discovered while comparing source and translation; record material corrections in the page translation artifact.

Perform a lightweight visual acceptance check immediately after rendering so obvious missing source text, clipping, unreadable text, or redraw damage is fixed before the page enters the persistence queue.

### qa

QA is performed by the same chapter worker. Visually inspect durable rendered pages for missing text, clipped text, unreadable layout, wrong order, untranslated reader-facing text, translation errors, or redraw damage. Fix issues directly and re-check them.

QA may only count a page backed by the exact remotely committed rendered asset being inspected. If QA changes an image, persist the corrected binary before advancing `qa_pages`.

### publish

After QA passes, create a valid publication manifest under:

`projects/<project>/publication/<chapter>/manifest.json`

The manifest must reference final localized assets, not raw source pages. The worker holding the live chapter fencing token may promote the final rendered bundle + manifest to `main` and mark the lane completed.

## Throughput-first persistence

Page completion is an atomic correctness boundary. Git persistence is a **batch boundary**.

Do not use this anti-pattern:

`render page -> blob -> tree -> commit -> ref -> lane/main update -> next page`

Use this pattern:

`render/accept page -> queue -> next page -> ... -> batch blobs -> one tree -> one commit -> one ref update -> continue`

Default steady-state checkpoint target is **6 completed pages**. Adapt roughly within **4-10 pages** according to file size, connector latency, and remaining runtime.

Force a checkpoint when any of these occurs:

- around 6 pages are queued;
- roughly 7 minutes have elapsed since the last durable checkpoint;
- pending binary payload is becoming risky/large;
- an internal phase reaches completion;
- minute 18-19 is reached with uncommitted completed work;
- drain begins.

The default batch checkpoint is:

`N page binaries -> N Git blobs -> 1 Git tree -> 1 Git commit -> 1 task-branch ref update`

Independent blob creation calls should be issued concurrently/parallel where the available tool runner supports that safely. Do not create N trees/commits/ref updates merely because the batch contains N pages.

Do not update chapter-lane state on `main` per page or per normal task-branch checkpoint. Main coordination state is normally written at claim and at final release/handoff or publish completion.

## Durable binary persistence

A rendered page is durable only after its final binary is present in a remote task-branch commit.

When local `git`/`curl` is unavailable, use the connected GitHub Git-data bridge:

1. optimize the finished page to WebP/JPEG where practical while preserving readability/fidelity;
2. target about <= 1 MiB/page when practical, but do not damage text/artwork merely to hit that target;
3. compute SHA-256 for final bytes;
4. base64-encode raw bytes without line wrapping;
5. create a Git blob with `encoding: base64`;
6. collect returned blob SHAs for the whole batch;
7. create one tree mapping all batch paths (`mode: 100644`, `type: blob`);
8. create one commit parented by the current task-branch head;
9. update the task branch ref once;
10. only after ref update succeeds advance the in-memory durable contiguous prefix.

Never store base64 text itself in the repository. Base64 is transport only.

## Cross-generation continuity

A new generation must inherit accumulated durable chapter work.

When the lane has a previous durable result commit, create the new generation branch from that checkpoint commit rather than from a clean `main` head. This keeps rendered pages and other accumulated chapter artifacts on one commit lineage and avoids later reconstruction during publish.

`last_result.commit` (or an explicitly recorded durable checkpoint head) is the preferred branch base for the next generation.

## Resume/checkpoint state

The lane stores at least:

- `phase`;
- `resume_page`;
- `progress.translated_pages`;
- `progress.rendered_pages`;
- `progress.qa_pages`;
- `progress.published`.

Progress counters are durability counters. In particular, `rendered_pages` counts only the contiguous rendered prefix present in a remote Git commit. Ephemeral local renders do not change lane progress.

When a phase reaches its last page, advance phase immediately and reset `resume_page` to 1. Continue in the same session if time remains.

## Runtime

For a 25-minute worker session:

- minute 0-2: state read, claim, inherit previous checkpoint, acquire/reuse relay;
- minute 2-18: continuous useful chapter work with adaptive batched checkpoints;
- minute 18-21: continue useful work while ensuring completed local backlog is flushed before it becomes risky;
- minute 21: drain begins;
- minute 21-23: finish the smallest safe unit already in progress, flush all queued artifacts, validate contiguous durable progress, write result/handoff;
- minute 24: only final bookkeeping/claim release.

There is no fixed or soft page-count stop. Continue until chapter completion or the runtime budget forces drain.

## Claim/fencing

`work/chapter_lanes/*.json` on `main` is coordinator state.

A runnable lane has `state` in `ready|partial` and `claim: null`. Claim it atomically using the current blob SHA. Lane `generation` is the session fencing token.

On partial handoff, persist exact `phase`/`resume_page`, clear claim, and increment generation. On successful publish, set `state: completed`, `phase: done`, `progress.published: true`, clear claim, and set `next_task: null`.

## Throughput rule

The chapter is the scheduling unit. Phases and pages are correctness/resume boundaries only. A worker must not voluntarily hand off because it completed one role, one phase, or a small arbitrary number of pages.
