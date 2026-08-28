from __future__ import annotations

import hashlib
import io
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedImage:
    format: str
    extension: str
    mime: str
    width: int
    height: int
    sha256: str


def verify_image(data: bytes, content_type: str | None) -> VerifiedImage:
    if not data:
        raise ValueError("empty response body")
    image_format, extension, dimensions = _identify(data)
    if image_format is None:
        raise ValueError("response body has no supported image signature")
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if mime and not (mime.startswith("image/") or mime == "application/octet-stream"):
        raise ValueError(f"response MIME is not an image: {mime}")
    if dimensions is None:
        dimensions = _pillow_dimensions(data)
    if dimensions is None or dimensions[0] < 1 or dimensions[1] < 1:
        raise ValueError(f"could not verify {image_format} dimensions")
    return VerifiedImage(
        format=image_format,
        extension=extension,
        mime=mime or f"image/{extension}",
        width=dimensions[0],
        height=dimensions[1],
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _identify(data: bytes) -> tuple[str | None, str, tuple[int, int] | None]:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return "png", "png", struct.unpack(">II", data[16:24])
    if data[:6] in {b"GIF87a", b"GIF89a"} and len(data) >= 10:
        return "gif", "gif", struct.unpack("<HH", data[6:10])
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg", "jpg", _jpeg_dimensions(data)
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp", "webp", _webp_dimensions(data)
    if len(data) >= 12 and data[4:12] in {b"ftypavif", b"ftypavis"}:
        return "avif", "avif", None
    return None, "bin", None


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            break
        segment_length = int.from_bytes(data[offset:offset + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if offset + 7 <= len(data):
                height = int.from_bytes(data[offset + 3:offset + 5], "big")
                width = int.from_bytes(data[offset + 5:offset + 7], "big")
                return width, height
            return None
        if segment_length < 2:
            return None
        offset += segment_length
    return None


def _webp_dimensions(data: bytes) -> tuple[int, int] | None:
    chunk = data[12:16]
    if chunk == b"VP8X" and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if chunk == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8 " and len(data) >= 30 and data[23:26] == b"\x9d\x01\x2a":
        width = int.from_bytes(data[26:28], "little") & 0x3FFF
        height = int.from_bytes(data[28:30], "little") & 0x3FFF
        return width, height
    return None


def _pillow_dimensions(data: bytes) -> tuple[int, int] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            return image.size
    except Exception:
        return None
