# Stateless Worker Start

Use this file as the single entrypoint for a fresh ChatGPT worker session on `tailolicon/manga-tl-factory`.

Do not rely on chat history, private memory, previous worker reasoning, or stale assumptions. `main` is the source of truth.

## Core execution model

**Every worker is a full-capability chapter localizer.**

There are no translator-only, redraw-only, typesetter-only, QA-only, or publisher-only workers. A worker may translate, correct translation, redraw, typeset, visually inspect, fix, QA, assemble, and publish.

Parallelism is by **non-overlapping page range**, not by role.

For `coordination_mode: parallel_ranges`, multiple workers may work on the same chapter at the same time. Each worker claims one page-range sublease and runs every remaining phase for that range:

`translate -> redraw_typeset -> qa -> done`

The global chapter finalization is:

`all ranges QA-complete -> assemble exact final blobs -> publication manifest -> publish -> chapter done`

Any generalist worker may become the finalizer. Finalization is a dependency state, not a separate worker role.

## Startup hot path

Read only:

1. `AGENTS.md`
2. `WORKER_PROTOCOL.md`
3. `TASK_PROTOCOL.md`
4. `CHAPTER_PIPELINE.md`
5. `config/pipeline.json`
6. `work/chapter_lanes/active.json`
7. the referenced active lane
8. only source/relay/result artifacts named by that lane or selected range

Do not recursively scan the repository.

Derive `python -m manga_factory chapter-envelope` semantics. The envelope selects one claimable range, or finalization when every range is complete.

## Parallel range claim

For a parallel lane, the chapter has no exclusive global worker claim. `lane.claim` must remain null. Coordination happens through `parallel.units[]`.

To claim a range:

1. Read the live lane and its current blob SHA.
2. Choose the range returned by `chapter-envelope`.
3. Require that range to be `ready|partial` with `claim: null`, or an expired claim explicitly marked reclaimable by the envelope.
4. Atomically update only that range entry on `main` using the live lane blob SHA.
5. Set its state to `claimed`, write `claimed_at` and `expires_at`, and preserve every other worker's range state exactly.
6. Use the range `generation` as its fencing token. A reclaimed expired range increments its range generation before work starts.
7. Create/reuse the range task branch named by the envelope. Start from that range's `checkpoint_commit` when resuming, otherwise from the lane's immutable `parallel.base_commit`.
8. If the lane changed before the claim write, refetch and choose again. Never overwrite another worker's claim.

Multiple workers can therefore race safely: CAS serialization happens only during the small claim/release writes; useful page work runs concurrently.

## Range ownership

A worker owns only the pages inside its claimed range. It must not modify rendered/translation paths belonging to another active range.

Within its range, the worker is full-stack:

- if phase is `translate`, translate then immediately continue to redraw/typeset and QA;
- if phase is `redraw_typeset`, finish redraw/typeset then immediately QA the same range;
- if phase is `qa`, inspect the exact durable rendered assets, fix failures directly, persist replacements, and finish the range.

Do not hand off merely because a phase boundary was crossed.

A completed range means every page in that range is QA-accepted and its exact final binary is durable on the range branch/result manifest.

## Throughput-first page loop

Use the whole 25-minute session for useful work.

Steady-state loop:

`claim range -> download/reuse relay once -> process pages continuously -> quick per-page visual acceptance -> queue outputs -> batch binary persistence -> continue -> QA range -> release/claim next range or finalize`

Rules:

- Never commit after every page unless payload/tool limits force it.
- Never update the lane after every page.
- Default binary checkpoint target is 6 completed pages; adapt roughly 4-10 pages.
- Force a checkpoint after about 7 minutes without one, at phase completion, around minute 18-19 if backlog exists, or at drain.
- One batch should normally be `N blobs -> 1 tree -> 1 commit -> 1 ref update`.
- Create independent Git blobs concurrently when the tool runner supports parallel calls.
- Reuse the chapter relay for the entire session.
- Do not re-investigate already-working Git binary transport.

## Binary persistence

For final rendered images, prefer WebP/JPEG while preserving publication quality and readable text.

When direct binary upload is unavailable:

1. compute SHA-256 of the exact final bytes;
2. base64-encode the bytes locally;
3. create a Git blob using `encoding: base64`;
4. collect blob SHAs for the batch;
5. create one tree with those page paths;
6. create one commit parented by the current range branch head;
7. update the range branch once;
8. only then count those outputs as durable.

Base64 is transport only and must never be stored as repository text.

Do not intentionally reduce pages to preview-quality resolution merely to minimize connector payload. Publication quality takes precedence. If a page is too large, optimize compression first; preserve source dimensions or a publication-appropriate resolution unless the source itself is smaller.

## Range result and release

Before releasing a range, write a structured range result containing every final page artifact:

- page index;
- repository path;
- Git blob SHA;
- SHA-256;
- width and height;
- durable branch commit;
- QA status.

On complete range:

1. persist all final binaries/result/handoff on the range branch;
2. refetch the live lane;
3. patch only your range entry using the new lane blob SHA;
4. set `state: completed`, `phase: done`, `claim: null`, and record the result commit/path;
5. do not rewrite other range entries.

On partial range:

1. persist completed work;
2. record exact phase/resume page/checkpoint commit;
3. refetch the live lane and patch only your range;
4. set `state: partial`, clear claim, increment that range generation for the next session.

A dead worker does not lock the chapter. Claims expire after the configured lease; a later worker may reclaim only that expired range.

## Claim another range in the same session

If your range completes with at least about 7 useful minutes remaining:

1. refetch the lane;
2. if another range is claimable, claim it atomically and keep working in the same session;
3. otherwise, if all ranges are completed and finalization is claimable, become the finalizer immediately.

Do not stop early just because one small range completed.

## Finalization

Finalization is allowed only when every range is `completed` with QA-accepted artifact manifests.

The finalizer must:

1. atomically claim `parallel.finalization` with its own fencing token/expiry;
2. read every completed range result;
3. verify complete page coverage with no overlap/gap and exact blob SHA for every page;
4. build the final publication tree from current `main`, inserting only final localized page blobs plus the publication manifest and required metadata;
5. create the publication manifest referencing those final assets;
6. promote one publication commit to `main`;
7. mark lane `state: completed`, `phase: done`, `progress.published: true`, finalization `completed`, and `next_task: null`.

Do not merge entire worker branch trees into `main`; promote only final publication assets/manifests/coordinator state.

## 25-minute budget

- Minute 0-2: startup, derive envelope, claim range/finalization, obtain relay/base checkpoint.
- Minute 2-18: continuous useful range work, crossing internal phases freely.
- Minute 18-21: continue useful work while keeping binary backlog safe; checkpoint if needed.
- Minute 21: enter drain.
- Minute 21-23: finish smallest safe unit, flush binaries/result/handoff, release range/finalization claim.
- Minute 23: durable recovery state should exist remotely.
- Minute 24: only minimal bookkeeping.

There is no soft page-count stop.

## Completion rule

A chapter is complete only when all page ranges are QA-complete, final assets have been assembled, a valid publication manifest exists on `main`, and `progress.published: true`.
