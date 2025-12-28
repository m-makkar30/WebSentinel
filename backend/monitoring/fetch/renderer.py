"""Headless-browser rendering via Playwright.

A ``PlaywrightRenderer`` owns one Chromium browser + one browser context and
reuses them across renders (context pooling). The instance is created lazily,
per worker process — Playwright's sync objects are not fork-safe, so we never
build them at import time, only on first use inside the (already-forked)
Celery worker child.

Polite fetching (robots.txt, pacing, API-first, block detection) is layered on
in the next commit; this module is just the rendering primitive.
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

# A realistic, honest user-agent: a normal Chrome UA with a WebSentinel token so
# site owners can identify the monitor in their logs.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 WebSentinel/0.1 (+monitoring)"
)


@dataclass
class RenderResult:
    url: str
    final_url: str
    http_status: int | None
    html: str
    screenshot_path: str  # relative to MEDIA_ROOT, "" if not captured
    duration_ms: int
    title: str = ""


class PlaywrightRenderer:
    """Owns a pooled Chromium browser/context for one worker process."""

    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._context = None

    def _ensure_context(self) -> None:
        if self._context is not None:
            return
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True,
            # --disable-dev-shm-usage avoids crashes on small /dev/shm in Docker.
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = self._browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1366, "height": 900},
            locale="en-US",
        )
        logger.info("Playwright browser context started")

    def render(
        self,
        url: str,
        *,
        timeout_ms: int = 30000,
        screenshot: bool = True,
    ) -> RenderResult:
        """Load ``url`` and return its rendered HTML, status, and a screenshot."""
        import time

        self._ensure_context()
        page = self._context.new_page()
        start = time.monotonic()
        try:
            response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            # Give late/XHR-driven content a chance to settle, but don't fail
            # the whole render if the network never goes fully idle.
            with contextlib.suppress(PlaywrightTimeoutError):
                page.wait_for_load_state("networkidle", timeout=5000)

            html = page.content()
            title = page.title()
            final_url = page.url
            status = response.status if response is not None else None

            screenshot_path = ""
            if screenshot:
                shots_dir = Path(settings.MEDIA_ROOT) / "screenshots"
                shots_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{uuid.uuid4().hex}.png"
                page.screenshot(path=str(shots_dir / filename), full_page=True)
                screenshot_path = str(Path("screenshots") / filename)

            duration_ms = int((time.monotonic() - start) * 1000)
            return RenderResult(
                url=url,
                final_url=final_url,
                http_status=status,
                html=html,
                screenshot_path=screenshot_path,
                duration_ms=duration_ms,
                title=title,
            )
        finally:
            page.close()

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
            if self._browser is not None:
                self._browser.close()
            if self._pw is not None:
                self._pw.stop()
        finally:
            self._pw = self._browser = self._context = None


# One renderer per worker process, created on first use.
_renderer: PlaywrightRenderer | None = None


def get_renderer() -> PlaywrightRenderer:
    global _renderer
    if _renderer is None:
        _renderer = PlaywrightRenderer()
    return _renderer
