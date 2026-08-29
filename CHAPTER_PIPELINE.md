# Chapter Production Pipeline

This is the production execution contract for `manga-tl-factory`.

## Generalist workers, parallel by range

The coordinator exposes one worker task type: `localize_chapter`.

Every worker is a generalist. Parallelism is achieved by assigning **non-overlapping page ranges**, never by splitting workers into translator/redraw/typesetter/QA roles.

For `coordination_mode: parallel_ranges`, each range runs every remaining local phase in order:

```text
translate -> redraw_typeset -> qa -> done
```

A range may begin at a later phase when earlier work is already durable. Phase boundaries are resume markers only. The same worker continues across them whenever time remains.

Chapter-wide finalization is dependency-driven:

```text
all ranges done -> verify coverage -> assemble final blobs -> manifest -> publish -> chapter done
```

Any normal generalist worker may claim finalization.

## Range partitioning

Ranges must not overlap. Prefer ranges sized to fit one 25-minute session based on observed throughput. For redraw/typeset-heavy work, roughly 4-8 pages per initial range is a useful default; the lane may choose another size from live evidence.

A parallel lane records `parallel.units[]`. Each unit has its own:

- `id`;
- `page_start` / `page_end`;
- `phase` and `resume_page`;
- `state`;
- `generation` fencing token;
- `claim` and expiry;
- `checkpoint_commit`;
- final `result`.

There is no exclusive chapter-wide worker claim in parallel mode. `lane.claim` stays null.

## Atomic subclaim protocol

Claims are coordinated by compare-and-swap on the lane file.

A worker:

1. reads the latest lane and blob SHA;
2. selects one claimable range returned by `chapter-envelope`;
3. patches only that range entry to `claimed` with `claimed_at`, `expires_at`, task id, branch, and fencing token;
4. writes the whole lane using the blob SHA it just read;
5. on conflict, refetches and selects again.

Because claim writes are tiny and useful work occurs on separate branches, many workers can operate on the same chapter concurrently.

A range claim expires after the configured lease. Reclaiming an expired range increments only that range's generation. A dead worker therefore cannot lock the whole chapter.

## Range branches and conflict avoidance

Every range has its own branch:

`chapter/<lane-id>/<range-id>/g<range-generation>`

A fresh range branch starts from immutable `parallel.base_commit`. A partial resumed range starts from its own `checkpoint_commit`.

Workers may write only page paths inside their claimed range plus their own result/handoff paths. Disjoint ranges therefore cannot overwrite one another's images.

Do not continuously merge range branches. Each completed range publishes a result manifest containing the exact final page blob SHAs. Chapter finalization assembles those manifests once.

## Phase rules inside a range

### translate

Inspect the source, translate all reader-facing text, and verify it. Persist page translation artifacts. Immediately continue to redraw/typeset when the page/range translation is ready.

### redraw_typeset

Use source + accepted translation, remove/cover source text as needed, typeset Vietnamese, then perform lightweight visual acceptance.

Final page path:

`projects/<project>/chapters/<chapter>/rendered/page-XXX.<ext>`

Correct obvious translation mistakes immediately when discovered.

### qa

Inspect the exact durable rendered asset. Check missing/untranslated text, clipping, readability, layout, wrong order, translation errors, and redraw damage. Fix failures directly and persist the replacement binary before marking the page accepted.

A range is `completed` only when every page in it is QA-accepted and its exact final binary is durable.

## Throughput-first persistence

Page correctness is atomic; Git persistence is batched.

Preferred loop:

`process/accept page -> queue -> next page -> ... -> batch blobs -> one tree -> one commit -> one ref update`

Default checkpoint target is around 6 pages, adaptive roughly 4-10 pages. Force a checkpoint after about 7 minutes without one, when payload becomes risky, at phase/range completion, around minute 18-19 with backlog, or at drain.

Independent blob creation calls should run concurrently when supported.

Do not update lane/main per page or per normal branch checkpoint.

## Binary durability

When direct binary upload is unavailable:

1. preserve publication-quality dimensions and readability;
2. optimize WebP/JPEG compression when practical;
3. compute SHA-256;
4. base64-encode exact bytes;
5. create Git blob with `encoding: base64`;
6. collect batch blob SHAs;
7. create one tree;
8. create one commit;
9. update the range branch once.

Base64 is transport only. Do not commit base64 text.

A tiny preview-resolution image is not acceptable merely because it is easier to upload. QA must replace any artifact that does not preserve publication-quality visual fidelity.

## Range result contract

A completed range result must enumerate every page with:

- page index;
- final repository path;
- Git blob SHA;
- SHA-256;
- width and height;
- durable commit;
- QA status.

The lane's unit result points to that result file/commit. Finalization treats these exact blob SHAs as source of truth.

## Same-session continuation

If a range completes with about 7 or more useful minutes remaining, the worker should refetch the lane and claim another range. If no range remains and all are completed, it should claim finalization and continue.

Completing a range is not automatically the end of a worker session.

## Finalization

`parallel.finalization` becomes claimable only when all units are completed.

The finalizer must:

1. claim finalization atomically;
2. read every range result;
3. verify pages 1..N are covered exactly once with no gaps or overlaps;
4. validate every artifact is QA-accepted and durable;
5. build a new tree based on current `main`, adding only final localized pages, publication manifest, required metadata, and final coordinator state;
6. create the publication manifest;
7. commit/promote the publication bundle to `main`;
8. set chapter `state: completed`, `phase: done`, `progress.published: true`, finalization completed, and `next_task: null`.

Do not merge whole WIP branch trees into main.

## Progress semantics

In parallel mode, global progress counters are aggregate durable counts and may complete out of page order. `parallel.units[]` is the authoritative source for ownership and completion.

The site must still consider the chapter unreadable until a publication manifest exists.

## Runtime

For each 25-minute worker session:

- minute 0-2: derive envelope, claim range/finalization, get relay/base checkpoint;
- minute 2-18: continuous useful work across local phases;
- minute 18-21: continue while keeping binary backlog safe;
- minute 21: drain;
- minute 21-23: flush, result/handoff, release subclaim;
- minute 24: minimal bookkeeping only.

There is no soft page-count stop.
