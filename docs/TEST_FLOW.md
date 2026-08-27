# First live test flow

When a real source URL is supplied:

1. Record it with `python -m manga_factory submit <URL>`.
2. Bootstrap worker inspects the source with its available browser/web/vision tools.
3. Bootstrap worker writes `projects/<id>/manifest.json` and proposes acquisition/vision/context discovery tasks.
4. Coordinator accepts/deduplicates proposals and schedules workers.
5. Context reviewers establish `Context v1` before mass translation.
6. Translation workers pin that context version and view original pages directly.
7. Chapter reviewer enforces continuity and voice across chunks.
8. Redraw/typeset/vision QA/final QA complete page assets.
9. Publisher emits `projects/<id>/publication/<chapter>.json` with CDN/object-store URLs.

For the first test, keep concurrency deliberately small until contracts and source acquisition behavior are verified; then increase the worker pool.
