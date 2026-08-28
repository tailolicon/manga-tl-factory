# Stateless Worker Start

Use this file as the single entrypoint for a fresh ChatGPT worker session on `tailolicon/manga-tl-factory`.

Do not rely on chat history, private memory, previous worker reasoning, or stale assumptions. `main` is the source of truth.

## Core execution model

**One worker session is a full-capability chapter-localization session.**

The worker is not a translator-only, redraw-only, QA-only, or publisher-only worker. It may translate, correct translation, redraw, typeset, visually inspect, fix, QA, and publish the same chapter in one session.

The chapter is the scheduling unit. Internal phases exist only as resumable checkpoints:

`translate -> redraw_typeset -> qa -> publish -> done`

A phase boundary is **never** a reason to stop or hand work to another worker. If the current phase finishes and useful time remains, immediately continue into the next phase.

The objective is to maximize **durable, correct chapter progress per 25-minute session**, not to maximize Git commits, tool calls, or role separation.

## Startup hot path

Read only:

1. `AGENTS.md`
2. `WORKER_PROTOCOL.md`
3. `TASK_PROTOCOL.md`
4. `CHAPTER_PIPELINE.md`
5. `config/pipeline.json`
6. `work/chapter_lanes/active.json`
7. the referenced active lane
8. only source/relay/artifact references named by that lane

Do not recursively scan the repository. Do not re-investigate mechanisms already declared working in these protocols.

## Envelope and claim

Derive `python -m manga_factory chapter-envelope` semantics.

For a runnable lane (`mode: chapter_pipeline`, `state` in `ready|partial`, `claim: null`):

1. Atomically claim the lane on `main` using the blob SHA just read.
2. Use lane `generation` as fencing token and `chapter-lane-<lane-id>-g<generation>` as lease.
3. Create/continue `chapter/<lane-id>/g<generation>` from the previous durable checkpoint commit when one is recorded. Do not restart accumulated chapter assets from `main`.
4. Execute `localize_chapter` beginning at lane `phase` and `resume_page`.
5. Keep the chapter for the whole session; do not voluntarily stop after a small page count.
6. Before ending, persist all completed work, write result/handoff, clear the claim, and increment generation unless publication completed the lane.

No external Shiro lease is required for an explicit active `chapter_pipeline` lane because the lane itself is coordinator state and fencing authority.

## Throughput-first work loop

The default steady-state loop is:

`claim -> load relay once -> process pages continuously in local runtime -> lightweight per-page visual acceptance -> queue completed outputs -> batch remote persistence -> continue processing -> final flush -> handoff/publish`

### Rules

- **Do not commit after every page.**
- **Do not update `main` after every page.** Main coordination writes are normally claim, final release/handoff, or final publish only.
- A page remains the atomic correctness boundary, but remote persistence cadence is a batch decision.
- After finishing a page locally and visually accepting it, immediately continue to the next page unless a checkpoint trigger below fires.
- Reuse the chapter relay already downloaded in the session. Never redownload the chapter per page.
- Avoid repeated repository reads, branch checks, or protocol checks inside the page loop unless an actual error requires them.
- When independent Git blob creation calls can be issued concurrently by the available tool runner, issue the batch concurrently/parallel instead of serially waiting between pages.

### Adaptive checkpoint policy

Use an adaptive batch, not a fixed one-page workflow.

Default checkpoint target: **6 completed pages**.

Adapt within roughly **4-10 pages** based on rendered file size and connector latency. Force a checkpoint when any of these is true:

1. about 6 completed pages are waiting locally;
2. roughly 7 minutes have passed since the last durable task-branch checkpoint;
3. pending binary payload is becoming large enough that one batch would be risky;
4. a phase is complete and its outputs must be durable before advancing;
5. the session reaches about minute 18-19 with any uncommitted completed work;
6. drain begins.

A checkpoint should normally be:

`N completed pages -> N Git blobs -> 1 tree -> 1 commit -> 1 branch-ref update`

Do **not** turn N pages into N trees/commits/ref updates.

If `create_blob` calls are independent, batch/parallelize them where supported, then perform the single tree/commit/ref update after all blob SHAs are available.

## Redraw/typeset hot path

For each page:

1. inspect source + accepted translation;
2. correct an obvious translation error immediately if discovered;
3. redraw/remove remaining source text as needed;
4. typeset Vietnamese;
5. perform a quick visual acceptance check for missing source text, clipping, unreadable text, or redraw damage;
6. save the accepted page locally in WebP/JPEG where practical;
7. queue it for the next binary checkpoint;
8. continue to the next page.

Do not perform a Git round-trip between steps 7 and 8 unless a checkpoint trigger fires.

## Binary checkpoint bridge

Missing local `git`, `curl`, or GitHub DNS is **not** a blocker when the connected GitHub capability exposes blob/tree/ref writes.

For each queued rendered page:

1. preserve visual quality and text readability; prefer WebP, or JPEG where appropriate;
2. target roughly <= 1 MiB/page when practical, but never destroy readability just to hit the target;
3. compute SHA-256 locally;
4. base64-encode raw image bytes without line wrapping;
5. create a Git blob with `encoding: base64`; base64 is transport only and must never be committed as text;
6. collect all blob SHAs for the batch;
7. create one tree containing all completed page paths;
8. create one commit parented by the current task-branch head;
9. advance the task branch once;
10. only after ref advancement succeeds count that contiguous prefix as durable.

`progress.rendered_pages` means contiguous rendered pages present in a remote Git commit. Ephemeral local images do not count.

## QA and fixes

QA is part of the same worker's job, not a different worker role.

If a rendered page fails QA, fix it immediately, re-check it, and replace its binary in the next checkpoint. Do not create a separate QA handoff merely because an issue was found.

If redraw/typeset reaches the last page with useful time left, start QA immediately. If QA finishes with useful time left, publish immediately.

## 25-minute budget

Treat the session as one 25-minute production slot.

- Minute 0-2: startup, live-state read, claim, branch/checkpoint inheritance, relay acquisition/reuse.
- Minute 2-18: continuous useful chapter work. Cross internal phase boundaries without stopping. Use adaptive batched checkpoints only when triggers fire.
- Minute 18-21: continue useful work, but ensure no large uncommitted backlog remains; force a rolling checkpoint if needed.
- Minute 21: enter `DRAINING`; do not start a large new page/operation that cannot safely finish.
- Minute 21-23: finish the smallest safe unit already in progress, flush all queued binaries/artifacts, validate contiguous durable progress, write result/handoff.
- Minute 23: durable result/handoff should already be remotely recoverable.
- Minute 24: only minimal claim release/final bookkeeping.

There is **no soft page-count stop**. Two or three pages are not a session target. Continue until chapter completion or the time budget forces drain.

## GitHub write policy

Use the authorized GitHub capability.

- `work/chapter_lanes/*.json` on `main` is coordinator state.
- Normal WIP lives on the chapter task branch.
- Do not write lane progress to `main` after every page or every checkpoint.
- Binary rendered assets use `create_blob(base64) -> create_tree -> create_commit -> update_ref` when direct local-file upload is unavailable.
- Preserve accumulated durable assets by basing each new generation branch on the previous generation's durable checkpoint commit when available.
- After QA passes, the same worker holding the live fencing token may promote final localized assets + publication manifest to `main` and mark the lane completed.

## Completion

A chapter is complete only when:

- `phase: done`;
- `progress.published: true`;
- a valid publication manifest exists and references the final localized assets.

Translation completion, redraw completion, or QA completion alone is not chapter completion and is not a reason to stop a session early.
