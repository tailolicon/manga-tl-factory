from __future__ import annotations

import json
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from .browser_bootstrap import BrowserSession, bootstrap_session
from .http_fetcher import PageFetchResult, assert_safe_url, fetch_page
from .models import ChapterSpec, PageSpec, SourceHandoff


BrowserBootstrap = Callable[..., BrowserSession]


def fetch_source(
    handoff_path: Path,
    *,
    result_path: Path | None = None,
    output_root: Path | None = None,
    concurrency: int = 6,
    timeout: float = 30.0,
    retries: int = 2,
    keep_temp: bool = False,
    allow_private_hosts: bool = False,
    browser_bootstrap: BrowserBootstrap = bootstrap_session,
) -> dict[str, object]:
    if not 1 <= concurrency <= 32:
        raise ValueError("concurrency must be between 1 and 32")
    handoff = SourceHandoff.load(handoff_path)
    result_path = result_path or handoff_path.with_name("fetch_result.json")
    scratch_root = output_root or Path(tempfile.gettempdir()) / "manga-factory"
    run_dir = scratch_root / _safe_component(handoff.project_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    chapter_results: list[dict[str, object]] = []
    warnings: list[str] = []
    browser_unavailable = False
    unresolved_pages = 0

    try:
        for chapter in handoff.chapters:
            chapter_started = time.perf_counter()
            chapter_dir = run_dir / _safe_component(chapter.chapter_id)
            outcomes = _fetch_batch(
                chapter.pages,
                chapter_dir,
                concurrency=concurrency,
                timeout=timeout,
                retries=retries,
                allow_private_hosts=allow_private_hosts,
            )
            failed_pages = [page for page in chapter.pages if not outcomes[page.index].success]
            if failed_pages:
                try:
                    assert_safe_url(chapter.source_url, allow_private_hosts)
                    session = browser_bootstrap(chapter.source_url, timeout_ms=45_000)
                except Exception as exc:
                    browser_unavailable = True
                    warnings.append(f"{chapter.chapter_id}: browser bootstrap failed: {str(exc)[:180]}")
                else:
                    browser_outcomes = _fetch_batch(
                        failed_pages,
                        chapter_dir,
                        concurrency=concurrency,
                        timeout=timeout,
                        retries=retries,
                        allow_private_hosts=allow_private_hosts,
                        fetch_mode="browser_bootstrap",
                        runtime_headers=session.headers,
                    )
                    for page in failed_pages:
                        retried = browser_outcomes[page.index]
                        retried.retry_count += outcomes[page.index].retry_count + 1
                        outcomes[page.index] = retried

            ordered = [outcomes[page.index] for page in chapter.pages]
            downloaded = sum(result.success for result in ordered)
            failed = len(ordered) - downloaded
            unresolved_pages += failed
            modes = {result.fetch_mode for result in ordered if result.success}
            fetch_mode = "browser_bootstrap" if "browser_bootstrap" in modes else "direct_http"
            chapter_results.append(
                {
                    "id": chapter.chapter_id,
                    "name": chapter.name,
                    "page_count": len(ordered),
                    "downloaded": downloaded,
                    "failed": failed,
                    "fetch_mode": fetch_mode,
                    "total_bytes": sum(result.bytes for result in ordered),
                    "elapsed_ms": round((time.perf_counter() - chapter_started) * 1000),
                    "concurrency": concurrency,
                    "retries": sum(result.retry_count for result in ordered),
                    "pages": [result.as_json() for result in ordered],
                }
            )

        status = "success" if unresolved_pages == 0 else "partial"
        result: dict[str, object] = {
            "schema": 1,
            "project_id": handoff.project_id,
            "status": status,
            "reason": None if status == "success" else (
                "browser_bootstrap_unavailable" if browser_unavailable else "android_runtime_required"
            ),
            "chapters": chapter_results,
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "warnings": warnings,
        }
        if keep_temp:
            result["retained_temp_dir"] = str(run_dir)
        _write_result(result_path, result)
        return result
    finally:
        if not keep_temp:
            shutil.rmtree(run_dir, ignore_errors=True)


def _fetch_batch(
    pages: tuple[PageSpec, ...] | list[PageSpec],
    chapter_dir: Path,
    *,
    concurrency: int,
    timeout: float,
    retries: int,
    allow_private_hosts: bool,
    fetch_mode: str = "direct_http",
    runtime_headers: dict[str, str] | None = None,
) -> dict[int, PageFetchResult]:
    outcomes: dict[int, PageFetchResult] = {}
    with ThreadPoolExecutor(max_workers=min(concurrency, len(pages))) as executor:
        futures = {
            executor.submit(
                fetch_page,
                page,
                chapter_dir,
                fetch_mode=fetch_mode,
                runtime_headers=runtime_headers,
                timeout=timeout,
                retries=retries,
                allow_private_hosts=allow_private_hosts,
            ): page.index
            for page in pages
        }
        for future in as_completed(futures):
            outcomes[futures[future]] = future.result()
    return outcomes


def _safe_component(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in "-_" else "-" for character in value)
    return cleaned.strip("-")[:96] or "unknown"


def _write_result(path: Path, result: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
