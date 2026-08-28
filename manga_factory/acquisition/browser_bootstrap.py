from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserSession:
    headers: dict[str, str]


def bootstrap_session(url: str, *, timeout_ms: int = 45_000) -> BrowserSession:
    """Open the source normally and return an in-memory HTTP session.

    This does not solve CAPTCHAs or persist browser state. Cookies are returned only to the
    current fetch process and must never be written to a result or handoff.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "browser bootstrap unavailable; install the optional playwright package and Chromium"
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(1_500)
            user_agent = page.evaluate("() => navigator.userAgent")
            cookies = context.cookies()
            cookie_header = "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in cookies)
            headers = {"User-Agent": user_agent}
            if cookie_header:
                headers["Cookie"] = cookie_header
            return BrowserSession(headers=headers)
        finally:
            browser.close()
