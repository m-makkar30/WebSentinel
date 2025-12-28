"""Anti-bot / CAPTCHA detection.

Detect-and-degrade only: we identify that a target is challenging us and stop,
marking it blocked. We never attempt to solve or circumvent challenges.
"""

from __future__ import annotations

# Lowercase substrings that strongly indicate an anti-bot interstitial.
BLOCK_MARKERS: tuple[str, ...] = (
    "captcha",
    "just a moment...",  # Cloudflare interstitial title
    "attention required! | cloudflare",
    "cf-chl",  # Cloudflare challenge tokens
    "challenge-platform",
    "/cdn-cgi/challenge",
    "pardon our interruption",  # HUMAN/PerimeterX
    "px-captcha",
    "access denied",
    "you have been blocked",
    "unusual traffic",
    "are you a robot",
    "verify you are human",
    "request unsuccessful. incapsula",
)


def detect(status: int | None, html: str) -> tuple[bool, str]:
    """Return (blocked, reason). Reason is empty when not blocked."""
    if status == 429:
        return True, "HTTP 429 (rate limited)"

    body = (html or "").lower()
    for marker in BLOCK_MARKERS:
        if marker in body:
            return True, f"anti-bot challenge detected ({marker!r})"

    if status == 403:
        return True, "HTTP 403 (forbidden — likely blocked)"
    return False, ""
