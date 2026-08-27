# Architecture

## Three layers

1. **Shiro / Coordinator**: scheduling, worker pool, leases, fencing tokens, retries, model calls.
2. **This repository**: workflow semantics, context rules, worker contracts, output formats.
3. **Model workers**: vision/reasoning and specialized task execution.

This separation allows Shiro or the model provider to change without rewriting the translation project format.

## Binary storage

Git should store text, manifests, hashes and history. Original/rendered page images should use object storage. Publication manifests are the stable interface to the website.

## Web publishing

A final chapter package is a JSON manifest referencing CDN/object-store page URLs. The website never needs to understand Shiro or worker internals.
