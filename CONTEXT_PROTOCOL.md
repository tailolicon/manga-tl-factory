# Context Protocol

## Principle

All translators of a series consume a shared, canonical, versioned context. No translator gets to silently redefine character voice or terminology.

## Canonical domains

- characters
- speech profiles
- terminology/names/places/abilities
- relationships
- timeline/story state
- style rules
- chapter summaries
- evidence/provenance

## Discovery vs canonicalization

```text
observation -> candidate -> evidence aggregation -> review -> canonical
```

Bootstrap/discovery workers produce candidates, not canonical truth.

## Provenance

Canonical claims must identify source evidence where possible, e.g.:

`ch012:p07:b03`

Context entries should include confidence and evidence references. Low-confidence claims stay candidates until reviewed.

## Versioning

Each canonical snapshot has an immutable `context_version`, normally a content hash. Tasks pin the version they used.

A context update must not silently rewrite historical task inputs. The coordinator can schedule a targeted consistency review for outputs produced with affected older context.

## Context compiler

Workers should consume a compiled task-specific bundle rather than loading the whole series blindly. A bundle can include:

- characters present in the scene
- relevant speech profiles
- relevant terminology
- recent chapter summaries
- relationship facts
- style rules
- pinned context version
- warnings/uncertain context
