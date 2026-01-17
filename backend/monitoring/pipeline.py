"""The per-target processing pipeline: fetch -> extract -> diff -> assess.

Shared by the Celery task and the demo runner so both behave identically.
Each run is recorded as a CheckRun (run history) and wrapped for resilience —
an unexpected failure is logged and recorded, never propagated as a crash.
"""

from __future__ import annotations

import logging
import time

from django.utils import timezone

from .fetch import fetcher
from .models import CheckRun, RunStatus, WatchTarget

logger = logging.getLogger(__name__)


def process_target(target: WatchTarget) -> dict:
    """Run one full check cycle for a target and return a JSON-safe summary."""
    started = timezone.now()
    t0 = time.monotonic()
    run = CheckRun(target=target, started_at=started, status=RunStatus.ERROR)
    summary: dict = {"target": str(target.uuid)}

    try:
        snapshot = fetcher.check_target(target)

        # Content-hash skip: unchanged page -> no snapshot, no downstream work.
        if snapshot is None:
            run.status = RunStatus.SKIPPED
            logger.info("check skipped (unchanged) target=%s", target.uuid)
            return {**summary, "skipped": True, "reason": "unchanged"}

        run.snapshot = snapshot
        run.fetch_method = snapshot.fetch_method
        run.http_status = snapshot.http_status

        change = None
        if snapshot.ok and not snapshot.blocked and snapshot.content_text:
            try:
                from .extract.extractor import extract as extract_snapshot

                extract_snapshot(snapshot)
            except Exception:
                logger.exception("extraction failed target=%s", target.uuid)

            try:
                from .diff.semantic import semantic_detect

                change = semantic_detect(target, snapshot)
            except Exception:
                logger.exception("change detection failed target=%s", target.uuid)

            if change is not None and change.is_meaningful:
                try:
                    from .assess.assessor import assess_change

                    assess_change(change)
                except Exception:
                    logger.exception("assessment failed change=%s", change.pk)

        run.change = change
        run.status = (
            RunStatus.BLOCKED
            if snapshot.blocked
            else (RunStatus.OK if snapshot.ok else RunStatus.ERROR)
        )
        logger.info(
            "checked target=%s method=%s ok=%s blocked=%s status=%s change=%s",
            target.uuid,
            snapshot.fetch_method,
            snapshot.ok,
            snapshot.blocked,
            snapshot.http_status,
            change.id if change else None,
        )
        return {
            **summary,
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
    except Exception as exc:
        run.status = RunStatus.ERROR
        run.error = str(exc)
        logger.exception("pipeline failed target=%s", target.uuid)
        return {**summary, "error": str(exc)}
    finally:
        run.finished_at = timezone.now()
        run.duration_ms = int((time.monotonic() - t0) * 1000)
        run.save()
