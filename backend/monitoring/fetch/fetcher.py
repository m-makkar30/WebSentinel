"""Polite fetch orchestration.

Doctrine (see README): respect robots.txt; consistent honest headers; pace
requests; API/feed first, browser second; detect anti-bot challenges and
degrade (mark blocked, alert, move on) — never circumvent.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from django.utils import timezone

from ..models import (
    Alert,
    AlertKind,
    FetchMethod,
    FetchStrategy,
    Severity,
    Snapshot,
    TargetStatus,
    WatchTarget,
)
from . import blocks, http_client, robots
from .renderer import get_renderer
from .textutil import content_hash, html_to_text

logger = logging.getLogger(__name__)

RAW_LIMIT = 1_000_000  # cap stored raw HTML (chars)
MIN_TEXT_FOR_HTML = 200  # below this, an HTML page likely needs JS rendering


@dataclass
class FetchOutcome:
    method: str
    ok: bool
    blocked: bool = False
    block_reason: str = ""
    http_status: int | None = None
    raw_html: str = ""
    content_text: str = ""
    final_url: str = ""
    screenshot_path: str = ""
    duration_ms: int = 0
    title: str = ""
    needs_browser: bool = False
    meta: dict = field(default_factory=dict)

    @property
    def hash(self) -> str:
        return content_hash(self.content_text) if self.content_text else ""


def _http_fetch(url: str) -> FetchOutcome:
    start = time.monotonic()
    try:
        resp = http_client.get(url)
    except Exception as exc:
        return FetchOutcome(
            method=FetchMethod.HTTP,
            ok=False,
            block_reason=f"http error: {exc}",
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    duration = int((time.monotonic() - start) * 1000)
    ctype = resp.headers.get("content-type", "").lower()
    html = resp.text
    blocked, reason = blocks.detect(resp.status_code, html)

    is_feed = any(token in ctype for token in ("xml", "rss", "atom", "json"))
    method = FetchMethod.API if is_feed else FetchMethod.HTTP
    text = html_to_text(html)
    needs_browser = (
        not is_feed
        and "text/html" in ctype
        and len(text) < MIN_TEXT_FOR_HTML
        and "<script" in html.lower()
    )
    return FetchOutcome(
        method=method,
        ok=resp.is_success and not blocked,
        blocked=blocked,
        block_reason=reason,
        http_status=resp.status_code,
        raw_html=html[:RAW_LIMIT],
        content_text=text,
        final_url=str(resp.url),
        duration_ms=duration,
        needs_browser=needs_browser,
        meta={"content_type": ctype},
    )


def _browser_fetch(url: str) -> FetchOutcome:
    result = get_renderer().render(url)
    blocked, reason = blocks.detect(result.http_status, result.html)
    status_ok = result.http_status is None or 200 <= result.http_status < 400
    return FetchOutcome(
        method=FetchMethod.BROWSER,
        ok=status_ok and not blocked,
        blocked=blocked,
        block_reason=reason,
        http_status=result.http_status,
        raw_html=result.html[:RAW_LIMIT],
        content_text=html_to_text(result.html),
        final_url=result.final_url,
        screenshot_path=result.screenshot_path,
        duration_ms=result.duration_ms,
        title=result.title,
    )


def fetch_target(target: WatchTarget) -> FetchOutcome:
    """Fetch a target per its strategy and the politeness doctrine."""
    allowed, reason = robots.allows(target.url)
    if not allowed:
        logger.info("skipping %s: %s", target.url, reason)
        return FetchOutcome(method=FetchMethod.HTTP, ok=False, blocked=True, block_reason=reason)

    if target.fetch_strategy == FetchStrategy.BROWSER:
        return _browser_fetch(target.url)

    outcome = _http_fetch(target.url)
    # API/feed first; escalate to the browser only on AUTO when HTML looks
    # JS-rendered (and we weren't blocked).
    if (
        outcome.needs_browser
        and target.fetch_strategy == FetchStrategy.AUTO
        and not outcome.blocked
    ):
        logger.info("escalating %s to browser render (sparse HTML)", target.url)
        return _browser_fetch(target.url)
    return outcome


def persist_outcome(target: WatchTarget, outcome: FetchOutcome) -> Snapshot:
    """Write a Snapshot and update target status, alerting on block/error."""
    now = timezone.now()
    snapshot = Snapshot.objects.create(
        target=target,
        fetched_at=now,
        fetch_method=outcome.method,
        http_status=outcome.http_status,
        ok=outcome.ok,
        blocked=outcome.blocked,
        status_note=outcome.block_reason,
        raw_content=outcome.raw_html,
        content_text=outcome.content_text,
        content_hash=outcome.hash,
        screenshot_path=outcome.screenshot_path,
        fetch_duration_ms=outcome.duration_ms,
        meta={**outcome.meta, "final_url": outcome.final_url, "title": outcome.title},
    )

    previous_status = target.status
    target.last_checked_at = now

    if outcome.blocked:
        target.status = TargetStatus.BLOCKED
        target.status_note = outcome.block_reason[:500]
        if previous_status != TargetStatus.BLOCKED:
            Alert.objects.create(
                target=target,
                kind=AlertKind.BLOCKED,
                level=Severity.MEDIUM,
                title=f"Target blocked: {target.name}",
                body=outcome.block_reason or "Anti-bot challenge or robots.txt disallow.",
            )
    elif not outcome.ok:
        target.status = TargetStatus.ERROR
        target.status_note = (outcome.block_reason or f"fetch failed (HTTP {outcome.http_status})")[
            :500
        ]
        if previous_status != TargetStatus.ERROR:
            Alert.objects.create(
                target=target,
                kind=AlertKind.ERROR,
                level=Severity.MEDIUM,
                title=f"Fetch error: {target.name}",
                body=target.status_note,
            )
    elif previous_status in (TargetStatus.BLOCKED, TargetStatus.ERROR):
        # Recovered.
        target.status = TargetStatus.ACTIVE
        target.status_note = ""

    target.save(update_fields=["status", "status_note", "last_checked_at", "updated_at"])
    return snapshot


def check_target(target: WatchTarget) -> Snapshot:
    return persist_outcome(target, fetch_target(target))
