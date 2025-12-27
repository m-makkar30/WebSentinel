import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="core.heartbeat")
def heartbeat() -> str:
    """Trivial periodic task that proves the Celery beat -> worker loop runs.

    Scheduled by Celery Beat (see CELERY_BEAT_SCHEDULE). Real monitoring tasks
    land in later commits.
    """
    timestamp = timezone.now().isoformat()
    logger.info("heartbeat ok at %s", timestamp)
    return timestamp
