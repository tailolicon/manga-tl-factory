# manga-tl-factory

Agent-first manga/comic localization workflow. The repository defines **how work is done**; an external coordinator such as Shiro defines **how work is scheduled**.

## Goals

- One source URL or uploaded archive becomes a structured translation project.
- Vision-first workers inspect original pages directly; OCR is optional supporting evidence.
- Every translator consumes the same versioned canonical story context.
- Workers never spawn workers. They return structured task proposals to the coordinator.
- Short disposable worker slices survive hard tool/runtime limits through checkpoints, handoffs, leases and fencing tokens managed by the coordinator.
- Final output is web-ready: publication manifests plus optimized page asset references.

## Boundary

### This repository owns

- pipeline DAG and worker role definitions
- project/source manifests
- context candidates and canonical context representation
- context compilation contracts
- translations/reviews/publication metadata
- worker result/task proposal schemas
- QA gates and web publication manifests

### External coordinator (Shiro) owns

- queue and task database
- atomic leasing and heartbeat
- fencing tokens / stale-worker rejection
- worker pool and concurrency
- retries, cancellation and timeouts
- branch/worktree/container lifecycle
- model invocation
- object-storage credentials

## Quick start

Fresh ChatGPT worker activation command:

```text
Run tailolicon/manga-tl-factory/WORKER_START.md from main.
```

The worker must treat that repository file as the complete stateless session entrypoint and follow its 25-minute drain/checkpoint budget.

Requires Python 3.11+ and no third-party Python packages for the reference CLI/tests.

```bash
python -m manga_factory submit "https://example.com/series/foo"
python -m manga_factory list-requests
python -m manga_factory test-envelope
python -m manga_factory validate
python -m unittest discover -s tests -v
```

## Kotori source acquisition test

Kotori may commit a small `source_handoff.json` containing one selected chapter's resolved page
URLs and only the safe request headers `Accept`, `Origin`, `Referer`, and `User-Agent`. It never
places image bytes, cookies, authorization headers, or an Android session in Git.

Fetch and verify the handoff with disposable local storage:

```bash
python -m manga_factory fetch-source work/imports/<project>/<run>/source_handoff.json
```

The acquisition worker downloads 4–8 pages concurrently (default 6), verifies the response MIME,
file signature, dimensions, non-zero size and SHA-256, and writes `fetch_result.json` next to the
handoff. Images live under the system temporary directory and are deleted after the run. Pass
`--keep-temp` only for an explicit visual/vision inspection.

Direct HTTP is always attempted first. Failed pages get one browser bootstrap for the chapter,
then return to the concurrent HTTP downloader with the in-memory browser session. Browser state is
never serialized. The optional fallback requires `playwright` plus a locally installed Chromium;
it does not solve CAPTCHAs or bypass source access controls.

### Automatic GitHub test run

Pushing a handoff to `work/imports/<project>/<run>/source_handoff.json` on `main` starts
`.github/workflows/source-acquisition.yml`. The job validates the repository, installs a disposable
headless Chromium, runs the same `fetch-source` CLI with concurrency 6, and uploads every generated
`fetch_result.json` as a 14-day GitHub Actions artifact. Source images stay only in the runner's
temporary directory and are deleted by the acquisition worker before the job ends.

The workflow can also be started manually with **Actions → Kotori source acquisition → Run
workflow** and a repository-relative handoff path. A partial result deliberately makes the job red
after the result artifact and performance summary have been uploaded. This MVP proves acquisition;
it does not start translation, persist raw images, or introduce R2/Android Bridge infrastructure.

`submit` does not scrape arbitrary websites. It records a normalized intake request. A bootstrap worker with browser/web access resolves the site and writes a source manifest according to `contracts/source_manifest.schema.json`.

Before a coordinator is installed, `STANDALONE_TEST.md` allows an explicit bootstrap-only test mode. It derives a deterministic test envelope from a pending intake request and permits an authorized GitHub connector to substitute for a local worktree.

## End-to-end workflow

```text
URL / archive
  -> bootstrap
  -> acquire_source
  -> vision_scan
  -> character/terminology/speech/story discovery
  -> context_review -> canonical context v1
  -> context compiler
  -> translation chunks
  -> chapter translation review
  -> redraw + typeset
  -> vision QA
  -> final QA
  -> publisher
  -> web publication manifest + CDN/object-storage assets
```

The pipeline is declared in `config/pipeline.json`, not hard-coded into Shiro.

## Worker runtime contract

Workers are expected to be short-lived. Default reference budget:

- normal work budget: 15 minutes
- begin draining: 18 minutes
- hard safety boundary: 22 minutes
- checkpoint after each completed page or other meaningful atomic unit

A worker nearing its budget must checkpoint, push its WIP branch when Git is available, emit `handoff.json`, and release its lease. If it dies first, the external coordinator lets the lease expire and reassigns the task. See `WORKER_PROTOCOL.md`.

## Context consistency

Canonical context is versioned and evidence-backed. Translation workers cannot directly modify it. They may only propose candidates. Context reviewers/integrators promote accepted candidates.

A translation task records the exact `context_version` used. If canonical context changes, the coordinator can schedule targeted consistency review rather than blindly retranslate everything.

## Publication contract

The production website should not read worker branches or intermediate files. A Publisher worker emits a manifest like:

```json
{
  "series_id": "example-series",
  "chapter_id": "42",
  "version": 3,
  "pages": [
    {
      "index": 1,
      "url": "https://cdn.example.com/manga/example-series/42/001.a812cf42.webp",
      "width": 1600,
      "height": 2400,
      "sha256": "..."
    }
  ]
}
```

The website only needs its metadata API/database plus CDN page URLs.

## Repository layout

```text
config/                 pipeline and quality configuration
contracts/              machine-readable worker/coordinator contracts
docs/                   design notes
manga_factory/          reference CLI and deterministic helpers
projects/<series>/       project-owned canonical data and text artifacts
requests/                URL/archive intake records
work/                    proposals/results/handoffs (normally ephemeral)
tests/                   deterministic reference tests
```

Large images should live in S3/R2/MinIO or another object store. Git stores manifests, hashes, context, translations and history.

## Copyright and source access

Use the pipeline for source material you own or are authorized to download, translate, modify and publish. Source adapters must respect access controls and site terms; the repository deliberately does not implement bypasses for protected sources.
