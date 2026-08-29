import base64
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from manga_factory.persistence_bridge import (
    PersistenceBridgeError,
    materialize_request,
    staged_paths,
    validate_request,
    write_receipt,
)


def make_webp(tmp_path: Path, *, size=(12, 7), quality=80) -> bytes:
    path = tmp_path / "fixture.webp"
    Image.new("RGB", size, (230, 220, 210)).save(path, "WEBP", quality=quality, method=6)
    return path.read_bytes()


def make_request(payload: bytes, *, width=12, height=7):
    encoded = base64.b64encode(payload).decode("ascii")
    chunks = [encoded[:16], encoded[16:32], encoded[32:]]
    blob_map = {
        hashlib.sha1(f"chunk-{i}".encode()).hexdigest(): chunk.encode("ascii")
        for i, chunk in enumerate(chunks)
        if chunk
    }
    request = {
        "schema": 1,
        "request_id": "unit-r015-020-g4",
        "target_branch": "chapter/stupidemic-ch1/r015-020/g4",
        "expected_head": "a" * 40,
        "files": [
            {
                "page": 15,
                "repository_path": "projects/demo/chapters/ch-1/rendered/page-015.webp",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "width": width,
                "height": height,
                "size_bytes": len(payload),
                "chunks": [{"blob_sha": sha} for sha in blob_map],
            }
        ],
    }
    return request, blob_map


def test_validate_rejects_path_traversal_and_non_chapter_branch(tmp_path):
    payload = make_webp(tmp_path)
    request, _ = make_request(payload)
    request["files"][0]["repository_path"] = "projects/demo/../../escape.webp"
    with pytest.raises(PersistenceBridgeError, match="unsafe repository path"):
        validate_request(request)

    request, _ = make_request(payload)
    request["target_branch"] = "main"
    with pytest.raises(PersistenceBridgeError, match="chapter"):
        validate_request(request)


def test_materialize_happy_path_exact_bytes_and_receipt(tmp_path):
    payload = make_webp(tmp_path)
    request, blobs = make_request(payload)
    normalized = validate_request(request)
    receipt = materialize_request(normalized, tmp_path / "repo", blobs.__getitem__)
    output = tmp_path / "repo" / normalized["files"][0]["repository_path"]
    assert output.read_bytes() == payload
    assert receipt["artifacts"][0]["sha256"] == hashlib.sha256(payload).hexdigest()
    assert receipt["artifacts"][0]["width"] == 12
    assert receipt["artifacts"][0]["height"] == 7
    receipt_path = write_receipt(receipt, tmp_path / "repo")
    persisted = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert persisted["expected_parent"] == "a" * 40
    assert staged_paths(normalized) == [
        "projects/demo/chapters/ch-1/rendered/page-015.webp",
        "work/persistence_receipts/unit-r015-020-g4.json",
    ]


def test_materialize_rejects_sha_mismatch(tmp_path):
    payload = make_webp(tmp_path)
    request, blobs = make_request(payload)
    request["files"][0]["sha256"] = "0" * 64
    with pytest.raises(PersistenceBridgeError, match="SHA-256 mismatch"):
        materialize_request(request, tmp_path / "repo", blobs.__getitem__)


def test_materialize_rejects_dimension_mismatch(tmp_path):
    payload = make_webp(tmp_path)
    request, blobs = make_request(payload, width=99, height=7)
    with pytest.raises(PersistenceBridgeError, match="dimension mismatch"):
        materialize_request(request, tmp_path / "repo", blobs.__getitem__)


def test_materialize_rejects_corrupt_or_missing_chunk(tmp_path):
    payload = make_webp(tmp_path)
    request, blobs = make_request(payload)
    first_sha = next(iter(blobs))
    blobs[first_sha] = b"!!!!"
    with pytest.raises(PersistenceBridgeError, match="not valid base64"):
        materialize_request(request, tmp_path / "repo", blobs.__getitem__)
