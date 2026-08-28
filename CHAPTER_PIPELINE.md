# Chapter Production Pipeline

This is the production execution contract for `manga-tl-factory`. It replaces the old smoke/test chapter flow for active work.

## One chapter, one task type

The coordinator exposes one task type: `localize_chapter`.

A worker claims one chapter and owns that chapter for the current session. Internal phases are checkpoints, not separate worker roles:

```text
translate -> redraw_typeset -> qa -> publish -> done
```

If a phase finishes and useful time remains, continue immediately into the next phase. Do not stop merely because a role/stage boundary was crossed.

## Phase rules

### translate

Inspect the source page directly, translate all reader-facing text, and verify the translation before marking the page complete. Store canonical page translation artifacts under:

`projects/<project>/chapters/<chapter>/translation/page-XXX.json`

Historical translation artifacts may be accepted as migration input when the lane explicitly pins their commit/path.

### redraw_typeset

For each page, use the source page plus the accepted translation to remove/cover source text where required and typeset the Vietnamese text. The same worker may perform redraw and typesetting. Store final localized page images under:

`projects/<project>/chapters/<chapter>/rendered/page-XXX.<ext>`

Raw source images are ephemeral and must not be committed. Final localized/rendered pages are publication outputs and may be committed.

Before typesetting a page, the worker may correct an obvious translation mistake discovered while comparing source and translation; record the correction in the page translation artifact.

#### Durable binary persistence

A rendered page is complete only after its final binary asset is durably committed to the remote task branch.

When the runtime cannot use local `git`/`curl` and the GitHub connector has no direct local-file parameter, use the Git data API bridge exposed by the connector:

1. optimize the finished page to WebP/JPEG when practical while preserving text readability and visual fidelity;
2. compute SHA-256 for the final bytes;
3. base64-encode those bytes;
4. create a Git blob with `encoding: base64`;
5. use the returned blob SHA in a tree entry for the rendered page path (`mode: 100644`, `type: blob`);
6. batch several completed page entries into one tree when practical;
7. create a commit on the current chapter task branch and update that branch ref;
8. only after the branch update succeeds may the worker advance the durable rendered-page count.

Never store the base64 representation itself in the repository. It is transport only.

Target approximately <= 1 MiB per rendered page when practical to reduce connector payload size. This is a transport target, not permission to make text unreadable or visibly damage artwork. If a page remains larger, use the smallest practical durable checkpoint batch rather than abandoning persistence.

### qa

Visually inspect rendered pages for missing text, clipped text, unreadable layout, wrong page order, untranslated reader-facing text, obvious translation errors, or redraw damage. Fix issues directly and re-check. QA is not a separate mandatory worker role.

QA may only count a page that is backed by the exact remotely committed rendered asset being inspected. If QA produces a corrected binary, persist the corrected blob/commit before advancing `qa_pages`.

### publish

After the chapter passes QA, create a valid publication manifest under:

`projects/<project>/publication/<chapter>/manifest.json`

The manifest must reference final localized page assets, not raw source pages. A publication-ready worker may promote the final rendered assets and manifest to `main` using the active chapter-lane fencing token. This is the only point at which the chapter is `completed`.

## Resume/checkpoint state

The active lane stores at least:

- `phase`: current phase;
- `resume_page`: first unfinished page in that phase;
- `progress.translated_pages`;
- `progress.rendered_pages`;
- `progress.qa_pages`;
- `progress.published`.

Progress counters are **durability counters**. In particular, `rendered_pages` counts only the contiguous rendered prefix that exists in a remote Git commit. Ephemeral local renders do not change the lane.

When a phase reaches the last page, advance `phase` immediately and reset `resume_page` to 1. Continue in the same session if time remains.

## Runtime

For a 25-minute worker session:

- minute 0-3: read state, claim, obtain/reuse chapter relay/source artifacts;
- minute 3-21: continuously advance the chapter, including crossing phase boundaries;
- during binary-producing work: make rolling Git blob/tree checkpoints instead of keeping all images local until drain;
- minute 21: drain begins;
- minute 21-23: finish the smallest safe atomic unit, persist artifacts and handoff;
- minute 24: only final bookkeeping/claim release.

Do not reserve time for a separate downstream worker if the current worker can safely continue.

## Claim/fencing

`work/chapter_lanes/*.json` on `main` is coordinator state.

A runnable lane has `state` in `ready|partial` and `claim: null`. Claim it atomically using the current blob SHA. The lane `generation` is the fencing token for that session.

On partial handoff, persist `phase` and `resume_page`, clear the claim, and increment `generation` for the next worker. On successful publish, set `state: completed`, `phase: done`, `progress.published: true`, clear the claim, and set `next_task: null`.

## Throughput rule

The chapter, not the page and not the phase, is the scheduling unit. Page boundaries are only correctness/checkpoint boundaries. Batch remote Git writes when practical.
