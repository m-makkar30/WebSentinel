import logging

from celery import shared_task

from .fetch.renderer import get_renderer

logger = logging.getLogger(__name__)


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
