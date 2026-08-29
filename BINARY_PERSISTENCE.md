# Exact-byte binary persistence bridge

This bridge exists for workers that already have QA-accepted final image bytes locally but cannot safely send one large base64 payload through the GitHub connector.

The bridge preserves the exact worker bytes. It does **not** re-render or reinterpret the page.

## Preferred transport

For a completed local image:

1. Compute the exact final byte length, SHA-256, width, and height.
2. Base64-encode the complete image bytes locally.
3. Split the base64 text on a multiple-of-4 boundary. Prefer chunks around 32 KiB of base64 text; keep every chunk below 64 KiB.
4. For each chunk, call GitHub `create_blob` with `encoding: utf-8`. The blob content is only that ASCII base64 chunk. Record each returned blob SHA in order.
5. Create one small request JSON on `main` under `work/persistence_requests/<request-id>.json`.
6. The `Range binary persistence` workflow fetches the staged chunk blobs, concatenates them, decodes the exact image bytes, verifies byte length/SHA-256/image dimensions, then commits the final binary files plus a receipt to the target range branch.
7. The workflow checks the target branch head before reconstruction and again before push. Its push uses `--force-with-lease` against `expected_head`. If another worker/checkpoint moved the range branch, the workflow fails instead of overwriting it.
8. Read `work/persistence_receipts/<request-id>.json` from the target branch and verify that the receipt's SHA-256 and Git blob SHA match the local QA-accepted bytes. Only then record the branch head as the durable page commit and complete/release the range.

Base64 chunk blobs are transport objects only. They are never committed as repository files and are not publication assets.

## Request shape

```json
{
  "schema": 1,
  "request_id": "chapter-stupidemic-ch1-r015-020-g4-persist-1",
  "target_branch": "chapter/stupidemic-ch1/r015-020/g4",
  "expected_head": "0123456789abcdef0123456789abcdef01234567",
  "files": [
    {
      "page": 15,
      "repository_path": "projects/example/chapters/ch-1/rendered/page-015.webp",
      "sha256": "<64 lowercase hex>",
      "width": 720,
      "height": 5000,
      "size_bytes": 112244,
      "chunks": [
        {"blob_sha": "<40 lowercase hex>"},
        {"blob_sha": "<40 lowercase hex>"}
      ]
    }
  ]
}
```

`target_branch` is restricted to `chapter/*`. Output paths are restricted to `projects/*` image paths. The receipt path defaults to `work/persistence_receipts/<request-id>.json`.

## Why this is preferred

Direct `create_blob(..., encoding=base64)` remains valid when a whole final image comfortably fits in one connector request. For long-strip WebP pages, the chunked bridge is preferred because it removes the single-request payload limit while preserving exact QA-approved bytes. It also avoids re-rendering on GitHub Actions, so SHA-256 identity remains the correctness fence.

## Failure semantics

A failed bridge run does not advance rendered/QA progress and does not mutate the chapter lane.

Typical failures are:

- invalid request/path/branch;
- missing or malformed chunk blob;
- decoded byte-length mismatch;
- SHA-256 mismatch;
- image decode/dimension mismatch;
- target branch head differs from `expected_head` before or during reconstruction;
- CAS push rejected because the range branch moved.

In every case, keep the range partial/claimed as appropriate, fix/reissue the transport request, and never fabricate durable blob identities.
