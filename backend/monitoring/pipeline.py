"""The per-target processing pipeline: fetch -> extract -> diff -> assess.

Shared by the Celery task and the demo runner so both behave identically.
"""

from __future__ import annotations

import logging

from .fetch import fetcher
from .models import WatchTarget

logger = logging.getLogger(__name__)


def process_target(target: WatchTarget) -> dict:
    """Run one full check cycle for a target and return a JSON-safe summary."""
    snapshot = fetcher.check_target(target)

    # Content-hash skip: unchanged page -> no snapshot, no downstream LLM work.
    if snapshot is None:
        logger.info("unchanged, skipped downstream work for %s", target.url)
        return {"target": str(target.uuid), "skipped": True, "reason": "unchanged"}

    change = None
    if snapshot.ok and not snapshot.blocked and snapshot.content_text:
        try:
            from .extract.extractor import extract as extract_snapshot

            extract_snapshot(snapshot)
        except Exception:
            logger.exception("extraction failed for %s", target.url)

        try:
            from .diff.semantic import semantic_detect

            change = semantic_detect(target, snapshot)
        except Exception:
            logger.exception("change detection failed for %s", target.url)

        if change is not None and change.is_meaningful:
            try:
                from .assess.assessor import assess_change

                assess_change(change)
            except Exception:
                logger.exception("assessment failed for change %s", change.pk)

    logger.info(
        "checked %s -> method=%s ok=%s blocked=%s status=%s fields=%d change=%s",
        target.url,
        snapshot.fetch_method,
        snapshot.ok,
        snapshot.blocked,
        snapshot.http_status,
        len(snapshot.extracted or {}),
        change.id if change else None,
    )
    return {
        "target": str(target.uuid),
        "snapshot_id": snapshot.id,
        "method": snapshot.fetch_method,
        "ok": snapshot.ok,
        "blocked": snapshot.blocked,
        "http_status": snapshot.http_status,
        "content_chars": len(snapshot.content_text),
        "extracted": snapshot.extracted,
        "change_id": change.id if change else None,
        "change_meaningful": bool(change and change.is_meaningful),
    }
