import logging

from celery import shared_task

from .fetch import fetcher
from .fetch.renderer import get_renderer
from .models import WatchTarget

logger = logging.getLogger(__name__)


@shared_task(name="monitoring.check_target")
def check_target(target_uuid: str) -> dict:
    """Polite fetch of one target: persists a Snapshot, handles blocks/errors.

    Routed to the `fetch` queue. Extraction and change detection are layered on
    top of this in later commits.
    """
    target = WatchTarget.objects.get(uuid=target_uuid)
    snapshot = fetcher.check_target(target)
    logger.info(
        "checked %s -> method=%s ok=%s blocked=%s status=%s hash=%s",
        target.url,
        snapshot.fetch_method,
        snapshot.ok,
        snapshot.blocked,
        snapshot.http_status,
        snapshot.content_hash[:12] or "-",
    )
    return {
        "target": str(target.uuid),
        "snapshot_id": snapshot.id,
        "method": snapshot.fetch_method,
        "ok": snapshot.ok,
        "blocked": snapshot.blocked,
        "http_status": snapshot.http_status,
        "content_chars": len(snapshot.content_text),
        "content_hash": snapshot.content_hash,
    }


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
