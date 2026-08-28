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

Inspect the source page directly, translate all player/reader-facing text, and verify the translation before marking the page complete. Store canonical page translation artifacts under:

`projects/<project>/chapters/<chapter>/translation/page-XXX.json`

Historical translation artifacts may be accepted as migration input when the lane explicitly pins their commit/path.

### redraw_typeset

For each page, use the source page plus the accepted translation to remove/cover source text where required and typeset the Vietnamese text. The same worker may perform redraw and typesetting. Store final localized page images under:

`projects/<project>/chapters/<chapter>/rendered/page-XXX.<ext>`

Raw source images are ephemeral and must not be committed. Final localized/rendered pages are publication outputs and may be committed.

Before typesetting a page, the worker may correct an obvious translation mistake discovered while comparing source and translation; record the correction in the page translation artifact.

### qa

Visually inspect rendered pages for missing text, clipped text, unreadable layout, wrong page order, untranslated reader-facing text, obvious translation errors, or redraw damage. Fix issues directly and re-check. QA is not a separate mandatory worker role.

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

When a phase reaches the last page, advance `phase` immediately and reset `resume_page` to 1. Continue in the same session if time remains.

## Runtime

For a 25-minute worker session:

- minute 0-3: read state, claim, obtain/reuse chapter relay/source artifacts;
- minute 3-21: continuously advance the chapter, including crossing phase boundaries;
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
