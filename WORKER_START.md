# Stateless Worker Start

Use this file as the single entrypoint for a fresh ChatGPT worker session on `tailolicon/manga-tl-factory`.

Do not rely on chat history, private memory, previous worker reasoning, or stale assumptions. `main` is the source of truth.

## Objective

Claim one active production chapter and advance it as far toward publication as the 25-minute session safely permits.

The chapter is the scheduling unit. Translation, redraw/typeset, QA and publish are internal phases of the same `localize_chapter` task. A worker that finishes one phase and still has time must continue into the next phase instead of stopping for another role/worker.

## Startup hot path

Read only:

1. `AGENTS.md`
2. `WORKER_PROTOCOL.md`
3. `TASK_PROTOCOL.md`
4. `CHAPTER_PIPELINE.md`
5. `config/pipeline.json`
6. `work/chapter_lanes/active.json`
7. the referenced active lane
8. only the source/relay/artifact references named by that lane

Do not recursively scan the repository.

## Envelope and claim

Derive `python -m manga_factory chapter-envelope` semantics.

For a runnable lane (`mode: chapter_pipeline`, `state` in `ready|partial`, `claim: null`):

1. Atomically claim the lane on `main` using the blob SHA just read.
2. Use lane `generation` as fencing token and `chapter-lane-<lane-id>-g<generation>` as lease.
3. Execute `localize_chapter` beginning at lane `phase` and `resume_page`.
4. Continue across phase boundaries in the same session whenever time remains.
5. Batch remote checkpoints where practical; page boundaries remain atomic correctness boundaries.
6. Before ending, persist phase/page progress, result/handoff, clear the claim and increment generation for the next worker unless publication completed the lane.

No external Shiro lease is required for an explicit active `chapter_pipeline` lane because the lane itself is the coordinator state and fencing authority.

## Phase behavior

Follow `CHAPTER_PIPELINE.md`.

Current phase order:

`translate -> redraw_typeset -> qa -> publish -> done`

Never stop merely because `translate` finished. If translation finishes at minute 12, start redraw/typeset immediately. If redraw finishes at minute 18, start QA immediately. If QA passes with enough time, publish immediately.

## Chapter relay

When the lane contains a ready relay artifact, download it once and reuse it for every page/phase in the session. Do not redownload individual source pages from the origin.

Raw source images stay ephemeral. Final localized/rendered pages are output artifacts and may be committed according to the publication rules.

## Binary checkpoint bridge

A missing local `git`, `curl`, or GitHub DNS route is **not** a binary-persistence blocker when the connected GitHub capability exposes blob/tree/ref writes.

For every completed rendered page:

1. Save the final page locally in a web-friendly format, preferably WebP (or JPEG when appropriate). Preserve legibility; target roughly <= 1 MiB per page when practical so connector payloads stay manageable.
2. Compute the page SHA-256 locally.
3. Base64-encode the raw image bytes without line wrapping.
4. Call the GitHub blob creation action with `encoding: base64` and that base64 payload. This creates a real Git binary blob; **do not commit the base64 text as a file**.
5. Collect the returned blob SHA for `projects/<project>/chapters/<chapter>/rendered/page-XXX.<ext>`.
6. After one or more page blobs are ready, create one Git tree using those blob SHAs, create a commit whose parent is the current task-branch head, then advance the task branch ref.
7. Verify the branch advanced successfully before counting those pages as durable.

`progress.rendered_pages` means **contiguous rendered pages durably present in a remote Git commit**, not pages that merely exist in ephemeral local storage. Never advance `rendered_pages` for an uncommitted local image.

If a connector rejects a payload because an individual image is too large, optimize/compress that page while preserving readable text and visual quality, then retry. Prefer several binary blobs + one tree/commit rather than one commit per page.

## 25-minute budget

- Minute 0-3: startup, claim, obtain/reuse source/relay inputs.
- Minute 3-21: continuously advance the claimed chapter across any phases that become ready.
- During redraw/typeset: make rolling binary checkpoints using the blob bridge so completed pages do not remain ephemeral for the whole session.
- Minute 21: enter drain; do not begin a large new operation.
- Minute 21-23: finish the smallest safe atomic unit, persist all completed work (including outstanding binary blobs), validate resume state, write result/handoff.
- Minute 23: resumable state should already be remotely recoverable.
- Minute 24: no substantive work; only minimal release/bookkeeping.

## GitHub writes

Use the authorized GitHub capability. `work/chapter_lanes/*.json` is coordinator state and may be updated directly on `main` with compare-and-swap semantics.

Normal WIP artifacts belong on the worker task branch. Text files may use normal file/tree writes. Binary rendered assets must use the Git blob base64 bridge described above when no direct local-file upload action is available.

After QA passes, the same worker may promote the final publication bundle (rendered pages + publication manifest) to `main` while holding the active fencing token, then mark the lane completed.

## Completion

A chapter is complete only when `phase: done`, `progress.published: true`, and a publication manifest exists. Translation completion alone is never chapter completion.
