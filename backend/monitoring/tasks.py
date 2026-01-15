import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .fetch.renderer import get_renderer
from .models import TargetStatus, WatchTarget
from .pipeline import process_target

logger = logging.getLogger(__name__)


@shared_task(name="monitoring.dispatch_due_checks")
def dispatch_due_checks() -> dict:
    """Beat-scheduled dispatcher: enqueue check_target for due active targets.

    A target is due when it has never been checked, or its last check is older
    than its own check_interval_minutes. This gives per-target cadence without
    managing a periodic-task row per target.
    """
    now = timezone.now()
    dispatched = 0
    for target in WatchTarget.objects.filter(status=TargetStatus.ACTIVE).only(
        "uuid", "last_checked_at", "check_interval_minutes"
    ):
        due = target.last_checked_at is None or (
            now - target.last_checked_at >= timedelta(minutes=target.check_interval_minutes)
        )
        if due:
            check_target.delay(str(target.uuid))
            dispatched += 1
    logger.info("dispatched %d due check(s)", dispatched)
    return {"dispatched": dispatched}


@shared_task(name="monitoring.check_target")
def check_target(target_uuid: str) -> dict:
    """Run the full check pipeline for one target. Routed to the `fetch` queue."""
    target = WatchTarget.objects.get(uuid=target_uuid)
    return process_target(target)


@shared_task(name="monitoring.render_url")
def render_url(url: str) -> dict:
    """Render a URL in the browser and return a small, JSON-safe summary.

    Routed to the dedicated ``fetch`` queue (see CELERY_TASK_ROUTES) consumed by
    the Playwright fetch worker. Persisting Snapshots and polite/API-first
    fetching are layered on in later commits.
    """
    result = get_renderer().render(url)
    logger.info(
        "rendered %s -> status=%s html=%dB shot=%s in %dms",
        url,
        result.http_status,
        len(result.html),
        result.screenshot_path or "-",
        result.duration_ms,
    )
    return {
        "url": result.url,
        "final_url": result.final_url,
        "http_status": result.http_status,
        "title": result.title,
        "html_bytes": len(result.html),
        "screenshot_path": result.screenshot_path,
        "duration_ms": result.duration_ms,
    }
