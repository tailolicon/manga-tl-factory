from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Callable

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
_BRANCH = re.compile(r"^chapter/[A-Za-z0-9._/-]+$")

MAX_FILES = 32
MAX_CHUNKS_PER_FILE = 128
MAX_CHUNK_TEXT_BYTES = 64 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_REQUEST_BYTES = 128 * 1024 * 1024


class PersistenceBridgeError(ValueError):
    """Raised when a persistence request or staged payload is invalid."""


def _safe_repo_path(value: object, *, prefix: str | None = None) -> str:
    if not isinstance(value, str) or not value:
        raise PersistenceBridgeError("repository path must be a non-empty string")
    if "\\" in value:
        raise PersistenceBridgeError(f"repository path must use '/': {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PersistenceBridgeError(f"unsafe repository path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise PersistenceBridgeError(f"repository path is not normalized: {value!r}")
    if prefix and not normalized.startswith(prefix.rstrip("/") + "/"):
        raise PersistenceBridgeError(f"repository path must be below {prefix!r}: {value!r}")
    return normalized


def validate_request(data: object) -> dict:
    if not isinstance(data, dict):
        raise PersistenceBridgeError("request must be a JSON object")
    if data.get("schema") != 1:
        raise PersistenceBridgeError("request schema must be 1")

    request_id = data.get("request_id")
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
        raise PersistenceBridgeError("invalid request_id")

    target_branch = data.get("target_branch")
    if not isinstance(target_branch, str) or not _BRANCH.fullmatch(target_branch) or ".." in target_branch:
        raise PersistenceBridgeError("target_branch must be a safe chapter/* branch")

    expected_head = data.get("expected_head")
    if not isinstance(expected_head, str) or not _HEX40.fullmatch(expected_head):
        raise PersistenceBridgeError("expected_head must be a lowercase 40-hex commit SHA")

    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise PersistenceBridgeError("files must be a non-empty list")
    if len(files) > MAX_FILES:
        raise PersistenceBridgeError(f"too many files; maximum is {MAX_FILES}")

    receipt_path = data.get("receipt_path") or f"work/persistence_receipts/{request_id}.json"
    receipt_path = _safe_repo_path(receipt_path, prefix="work/persistence_receipts")

    seen_pages: set[int] = set()
    seen_paths: set[str] = set()
    total_size = 0
    normalized_files: list[dict] = []

    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise PersistenceBridgeError(f"files[{index}] must be an object")
        page = item.get("page")
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise PersistenceBridgeError(f"files[{index}].page must be a positive integer")
        if page in seen_pages:
            raise PersistenceBridgeError(f"duplicate page: {page}")
        seen_pages.add(page)

        repository_path = _safe_repo_path(item.get("repository_path"), prefix="projects")
        if repository_path in seen_paths:
            raise PersistenceBridgeError(f"duplicate repository_path: {repository_path}")
        seen_paths.add(repository_path)
        if Path(repository_path).suffix.lower() not in {".webp", ".jpg", ".jpeg", ".png"}:
            raise PersistenceBridgeError(f"unsupported image extension: {repository_path}")

        sha256 = item.get("sha256")
        if not isinstance(sha256, str) or not _HEX64.fullmatch(sha256):
            raise PersistenceBridgeError(f"files[{index}].sha256 must be lowercase 64-hex")

        width = item.get("width")
        height = item.get("height")
        if not isinstance(width, int) or isinstance(width, bool) or width < 1:
            raise PersistenceBridgeError(f"files[{index}].width must be a positive integer")
        if not isinstance(height, int) or isinstance(height, bool) or height < 1:
            raise PersistenceBridgeError(f"files[{index}].height must be a positive integer")

        size_bytes = item.get("size_bytes")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 1:
            raise PersistenceBridgeError(f"files[{index}].size_bytes must be a positive integer")
        if size_bytes > MAX_FILE_BYTES:
            raise PersistenceBridgeError(f"files[{index}] exceeds {MAX_FILE_BYTES} bytes")
        total_size += size_bytes
        if total_size > MAX_REQUEST_BYTES:
            raise PersistenceBridgeError(f"request exceeds {MAX_REQUEST_BYTES} bytes")

        chunks = item.get("chunks")
        if not isinstance(chunks, list) or not chunks:
            raise PersistenceBridgeError(f"files[{index}].chunks must be a non-empty list")
        if len(chunks) > MAX_CHUNKS_PER_FILE:
            raise PersistenceBridgeError(
                f"files[{index}] has too many chunks; maximum is {MAX_CHUNKS_PER_FILE}"
            )
        normalized_chunks: list[str] = []
        for chunk_index, chunk in enumerate(chunks):
            blob_sha = chunk.get("blob_sha") if isinstance(chunk, dict) else chunk
            if not isinstance(blob_sha, str) or not _HEX40.fullmatch(blob_sha):
                raise PersistenceBridgeError(
                    f"files[{index}].chunks[{chunk_index}] must contain a lowercase 40-hex blob_sha"
                )
            normalized_chunks.append(blob_sha)

        normalized_files.append(
            {
                "page": page,
                "repository_path": repository_path,
                "sha256": sha256,
                "width": width,
                "height": height,
                "size_bytes": size_bytes,
                "chunks": normalized_chunks,
            }
        )

    return {
        "schema": 1,
        "request_id": request_id,
        "target_branch": target_branch,
        "expected_head": expected_head,
        "receipt_path": receipt_path,
        "files": normalized_files,
    }


def load_request(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PersistenceBridgeError(f"cannot read request {path}: {exc}") from exc
    return validate_request(raw)


def _git_blob_sha(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def probe_image_dimensions(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - workflow installs Pillow
        raise PersistenceBridgeError("Pillow is required to verify image dimensions") from exc
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception as exc:
        raise PersistenceBridgeError(f"invalid image {path}: {exc}") from exc


def materialize_request(
    request: dict,
    output_root: Path,
    blob_loader: Callable[[str], bytes],
) -> dict:
    request = validate_request(request)
    output_root = output_root.resolve()
    artifacts: list[dict] = []

    for item in request["files"]:
        encoded_parts: list[str] = []
        for blob_sha in item["chunks"]:
            raw_chunk = blob_loader(blob_sha)
            if not isinstance(raw_chunk, (bytes, bytearray)):
                raise PersistenceBridgeError(f"blob loader returned non-bytes for {blob_sha}")
            if len(raw_chunk) > MAX_CHUNK_TEXT_BYTES:
                raise PersistenceBridgeError(
                    f"staged chunk {blob_sha} exceeds {MAX_CHUNK_TEXT_BYTES} bytes"
                )
            try:
                encoded_parts.append(bytes(raw_chunk).decode("ascii"))
            except UnicodeDecodeError as exc:
                raise PersistenceBridgeError(f"staged chunk {blob_sha} is not ASCII") from exc

        encoded = "".join(encoded_parts)
        try:
            payload = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise PersistenceBridgeError(
                f"staged chunks for page {item['page']} are not valid base64"
            ) from exc

        if len(payload) != item["size_bytes"]:
            raise PersistenceBridgeError(
                f"page {item['page']} size mismatch: expected {item['size_bytes']}, got {len(payload)}"
            )
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != item["sha256"]:
            raise PersistenceBridgeError(
                f"page {item['page']} SHA-256 mismatch: expected {item['sha256']}, got {actual_sha256}"
            )

        destination = (output_root / item["repository_path"]).resolve()
        try:
            destination.relative_to(output_root)
        except ValueError as exc:
            raise PersistenceBridgeError(f"output escapes repository root: {destination}") from exc
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)

        width, height = probe_image_dimensions(destination)
        if (width, height) != (item["width"], item["height"]):
            destination.unlink(missing_ok=True)
            raise PersistenceBridgeError(
                f"page {item['page']} dimension mismatch: expected "
                f"{item['width']}x{item['height']}, got {width}x{height}"
            )

        artifacts.append(
            {
                "page": item["page"],
                "repository_path": item["repository_path"],
                "git_blob_sha": _git_blob_sha(payload),
                "sha256": actual_sha256,
                "width": width,
                "height": height,
                "size_bytes": len(payload),
                "qa": "exact_bytes_reconstructed_pending_durable_commit",
            }
        )

    return {
        "schema": 1,
        "status": "materialized",
        "request_id": request["request_id"],
        "target_branch": request["target_branch"],
        "expected_parent": request["expected_head"],
        "receipt_path": request["receipt_path"],
        "artifacts": artifacts,
    }


def write_receipt(receipt: dict, output_root: Path) -> Path:
    receipt_path = _safe_repo_path(receipt.get("receipt_path"), prefix="work/persistence_receipts")
    destination = output_root.resolve() / receipt_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def github_blob_loader(repository: str, token: str) -> Callable[[str], bytes]:
    if not repository or "/" not in repository:
        raise PersistenceBridgeError("repository must be owner/name")
    if not token:
        raise PersistenceBridgeError("GitHub token is required")

    def load(blob_sha: str) -> bytes:
        if not _HEX40.fullmatch(blob_sha):
            raise PersistenceBridgeError(f"invalid staged blob SHA: {blob_sha}")
        url = f"https://api.github.com/repos/{repository}/git/blobs/{blob_sha}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "manga-tl-factory-persistence-bridge",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise PersistenceBridgeError(f"cannot fetch staged blob {blob_sha}: {exc}") from exc
        if data.get("encoding") != "base64" or not isinstance(data.get("content"), str):
            raise PersistenceBridgeError(f"unexpected GitHub blob response for {blob_sha}")
        try:
            return base64.b64decode(data["content"], validate=False)
        except Exception as exc:
            raise PersistenceBridgeError(f"cannot decode GitHub blob {blob_sha}") from exc

    return load


def staged_paths(request: dict) -> list[str]:
    request = validate_request(request)
    return [item["repository_path"] for item in request["files"]] + [request["receipt_path"]]
