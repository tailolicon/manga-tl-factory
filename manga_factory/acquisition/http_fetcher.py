from __future__ import annotations

import ipaddress
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from .models import PageSpec
from .verify import verify_image

MAX_PAGE_BYTES = 100 * 1024 * 1024


@dataclass
class PageFetchResult:
    index: int
    success: bool
    fetch_mode: str
    http_status: int | None
    dns_ms: int
    ttfb_ms: int
    download_ms: int
    bytes: int
    retry_count: int
    mime: str | None = None
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    error: str | None = None

    def as_json(self) -> dict[str, object]:
        return asdict(self)


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allow_private_hosts: bool) -> None:
        super().__init__()
        self.allow_private_hosts = allow_private_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        assert_safe_url(newurl, self.allow_private_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_page(
    page: PageSpec,
    output_dir: Path,
    *,
    fetch_mode: str = "direct_http",
    runtime_headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    retries: int = 2,
    allow_private_hosts: bool = False,
) -> PageFetchResult:
    last_error = "download failed"
    last_status: int | None = None
    last_dns = 0
    last_ttfb = 0
    last_download = 0
    opener = urllib.request.build_opener(SafeRedirectHandler(allow_private_hosts))
    headers = dict(page.headers)
    headers.update(runtime_headers or {})
    headers.setdefault("User-Agent", "MangaFactory-Fetch/0.1")
    headers.setdefault("Accept", "image/avif,image/webp,image/apng,image/*,*/*;q=0.8")

    for attempt in range(retries + 1):
        try:
            dns_started = time.perf_counter()
            assert_safe_url(page.url, allow_private_hosts)
            last_dns = round((time.perf_counter() - dns_started) * 1000)
            request = urllib.request.Request(page.url, headers=headers, method="GET")
            request_started = time.perf_counter()
            with opener.open(request, timeout=timeout) as response:
                last_ttfb = round((time.perf_counter() - request_started) * 1000)
                last_status = getattr(response, "status", 200)
                assert_safe_url(response.geturl(), allow_private_hosts)
                download_started = time.perf_counter()
                data = response.read(MAX_PAGE_BYTES + 1)
                last_download = round((time.perf_counter() - download_started) * 1000)
                if len(data) > MAX_PAGE_BYTES:
                    raise ValueError("page exceeds the 100 MiB safety limit")
                verified = verify_image(data, response.headers.get("Content-Type"))
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / f"{page.index:04d}.{verified.extension}").write_bytes(data)
            return PageFetchResult(
                index=page.index,
                success=True,
                fetch_mode=fetch_mode,
                http_status=last_status,
                dns_ms=last_dns,
                ttfb_ms=last_ttfb,
                download_ms=last_download,
                bytes=len(data),
                retry_count=attempt,
                mime=verified.mime,
                width=verified.width,
                height=verified.height,
                sha256=verified.sha256,
            )
        except urllib.error.HTTPError as exc:
            last_status = exc.code
            last_error = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = str(exc)
        if attempt < retries:
            time.sleep(min(0.25 * (2**attempt), 1.0))

    return PageFetchResult(
        index=page.index,
        success=False,
        fetch_mode=fetch_mode,
        http_status=last_status,
        dns_ms=last_dns,
        ttfb_ms=last_ttfb,
        download_ms=last_download,
        bytes=0,
        retry_count=retries,
        error=last_error[:240],
    )


def assert_safe_url(url: str, allow_private_hosts: bool) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only absolute HTTP(S) page URLs are supported")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses:
        raise ValueError("hostname did not resolve")
    if allow_private_hosts:
        return
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise ValueError(f"refusing non-public address for {parsed.hostname}")
