"""robots.txt compliance. Cached per host; fail-open when robots is missing."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from .constants import HTTP_HEADERS, HTTP_TIMEOUT, ROBOTS_UA_TOKEN

logger = logging.getLogger(__name__)

_cache: dict[str, RobotFileParser] = {}


def _base(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _load(base: str) -> RobotFileParser:
    rp = RobotFileParser()
    robots_url = f"{base}/robots.txt"
    rp.set_url(robots_url)
    try:
        resp = httpx.get(
            robots_url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT, follow_redirects=True
        )
        # 2xx -> apply rules; anything else (404, etc.) -> no rules -> allow all.
        rp.parse(resp.text.splitlines() if resp.status_code == 200 else [])
    except httpx.HTTPError as exc:
        logger.warning("robots fetch failed for %s (%s); allowing", base, exc)
        rp.parse([])
    return rp


def allows(url: str) -> tuple[bool, str]:
    """Return (allowed, reason). Reason is empty when allowed."""
    base = _base(url)
    rp = _cache.get(base)
    if rp is None:
        rp = _load(base)
        _cache[base] = rp
    if rp.can_fetch(ROBOTS_UA_TOKEN, url):
        return True, ""
    return False, "disallowed by robots.txt"
