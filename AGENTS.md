# AGENTS.md

Repository instructions override model priors for this project.

## Source of truth

1. `config/pipeline.json`
2. `WORKER_PROTOCOL.md`
3. `CONTEXT_PROTOCOL.md`
4. `TASK_PROTOCOL.md`
5. contract schemas under `contracts/`
6. the selected project's canonical context and manifest

## Core rules

- Never spawn another worker directly.
- Return structured `task_proposals`; the external coordinator alone creates/schedules tasks.
- Never work without a valid coordinator-issued lease/fencing token in production.
- Never push directly to `main` from a worker.
- Translation/review workers must not directly modify canonical context.
- Every assertion promoted into canonical context needs provenance/evidence.
- Vision is the primary interpretation path for page meaning; OCR is supporting evidence.
- Use the task's pinned `context_version` and record it in every result.
- Checkpoint after meaningful atomic units, especially every completed page.
- Begin draining before the runtime hard limit; do not rely on final-minute cleanup.
- Submit uncertainty explicitly. Do not invent speaker identity, terminology or missing source text.
- Large binary images belong in object storage, not normal Git history.
