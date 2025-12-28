"""Polite HTTP client: a persistent session (cookie reuse) with per-host pacing."""

from __future__ import annotations

import random
import threading
import time
from urllib.parse import urlsplit

import httpx

from .constants import HTTP_HEADERS, HTTP_TIMEOUT, MIN_REQUEST_INTERVAL

_last_request: dict[str, float] = {}
_lock = threading.Lock()

# One persistent client per worker process keeps cookies/connections warm.
_client: httpx.Client | None = None


def _domain(url: str) -> str:
    return urlsplit(url).netloc.lower()


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            headers=HTTP_HEADERS,
            follow_redirects=True,
            timeout=HTTP_TIMEOUT,
        )
    return _client


def pace(url: str) -> None:
    """Sleep so requests to the same host stay at least MIN_REQUEST_INTERVAL apart."""
    domain = _domain(url)
    with _lock:
        elapsed = time.monotonic() - _last_request.get(domain, 0.0)
        wait = MIN_REQUEST_INTERVAL - elapsed
    if wait > 0:
        time.sleep(wait + random.uniform(0.0, 0.5))  # small jitter
    with _lock:
        _last_request[domain] = time.monotonic()


def get(url: str) -> httpx.Response:
    pace(url)
    return _get_client().get(url)
