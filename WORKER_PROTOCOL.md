# Worker Protocol

## Execution lifecycle

Active chapter work uses a durable chapter lane on `main` plus one short-lived branch per claimed page range.

```text
CLAIMED -> RUNNING -> DRAINING -> SUBMITTED
                   -> FAILED
```

Every worker is a generalist chapter localizer.

## Parallel production ownership

For `coordination_mode: parallel_ranges`, no worker exclusively owns the whole chapter. Workers own non-overlapping page ranges.

The task type remains `localize_chapter`. Translation, correction, redraw, typesetting, QA, fixes, assembly and publish are capabilities of the same worker type, not separate roles.

Within a claimed range, continue across all remaining phases whenever runtime allows.

## Range fencing

Each `parallel.units[]` entry has its own `generation`. That range generation is the fencing token for work on that range.

A worker must mutate only its own range entry when claiming/releasing. It must preserve all other range entries from the latest lane read.

Claim and release writes use compare-and-swap against the current lane blob SHA. If another worker updated the lane first, refetch and retry against the new state.

A range claim contains an expiry. A dead worker can block only its range until expiry. Reclaiming an expired range increments that range generation before useful work starts.

The global lane `generation` is a coordination epoch, not the fencing token for every parallel worker.

## Branch policy

Range branches are named:

`chapter/<lane-id>/<range-id>/g<range-generation>`

A fresh range starts from immutable `parallel.base_commit`. A resumed partial range starts from its own `checkpoint_commit`.

Workers may modify only paths for their claimed range plus their own result/handoff files.

Do not merge range branches during normal work. Range result manifests provide the exact blob SHAs for final assembly.

## Runtime budget

- minute 0-2: derive envelope, claim range, create/reuse branch, get relay;
- minute 2-18: continuous useful work;
- minute 18-21: continue while bounding uncommitted backlog;
- minute 21: drain begins;
- by minute 23: result/handoff and release should be durable;
- minute 24: bookkeeping only.

There is no page-count stop condition.

## Checkpoint policy

Page correctness and Git persistence cadence are separate.

Default batch target: 6 pages, adaptive roughly 4-10. Force checkpoint after roughly 7 minutes without one, at phase/range completion, when payload becomes risky, around minute 18-19 with backlog, or at drain.

Normal batch:

`N create_blob -> 1 create_tree -> 1 create_commit -> 1 update_ref`

Run independent blob creation calls concurrently when supported.

Do not update lane/main per page or per ordinary task-branch checkpoint.

## Binary assets

When direct binary upload is unavailable, use the Git data bridge:

1. preserve publication-quality resolution and readable text;
2. optimize WebP/JPEG compression where practical;
3. compute SHA-256;
4. base64-encode exact bytes;
5. create Git blob with `encoding: base64`;
6. create one batch tree/commit/ref update.

Base64 is transport only.

Do not intentionally downscale to preview resolution solely to make connector transport easier. QA must replace such artifacts before range completion.

## Range completion

A range is complete only when every page in it has passed QA and the exact final binaries are durable.

The range result must enumerate final page index/path/blob SHA/SHA-256/dimensions/QA status and durable commit.

On complete:

- persist result/handoff;
- refetch lane;
- patch only your unit to `completed`, `phase: done`, `claim: null`, and record result/checkpoint commit.

On partial:

- persist checkpoint/result/handoff;
- refetch lane;
- patch only your unit to `partial` with exact phase/resume/checkpoint;
- clear claim and increment that unit generation.

If at least ~7 useful minutes remain after range completion, claim another ready range. Do not end the session just because one range finished.

## Finalization fencing

`parallel.finalization` has its own generation/claim/expiry. It becomes claimable only when every range is completed.

Any generalist worker may claim it. The finalizer verifies all range result manifests, checks exact page coverage, assembles final localized page blobs, creates publication manifest, promotes only publication outputs to `main`, and marks the chapter completed.

## Git safety

Never promote raw source images or whole WIP range branch trees to `main`.

Final publication must be constructed from current `main` plus the exact QA-approved rendered page blobs and manifest/coordinator state.

## Legacy mode

Single-claim chapter lanes remain compatibility-only. Fresh production lanes should use `coordination_mode: parallel_ranges`.
