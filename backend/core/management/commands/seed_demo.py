from django.core.management.base import BaseCommand

from monitoring.models import FetchStrategy, Vertical, WatchTarget

# Monitoring-friendly, robots-respecting public feeds/APIs that genuinely change
# over time and need no browser (per the fetch doctrine). example.com is a
# stable control that should never raise a meaningful change.
DEMO_TARGETS = [
    {
        "name": "US Federal Register — latest documents",
        "url": "https://www.federalregister.gov/api/v1/documents.json?per_page=20&order=newest",
        "vertical": Vertical.REGULATORY,
        "watch_instructions": "New federal rules, notices, and proposed regulations.",
        "fetch_strategy": FetchStrategy.API,
        "check_interval_minutes": 360,
    },
    {
        "name": "Hacker News — newest",
        "url": "https://hnrss.org/newest",
        "vertical": Vertical.GENERIC,
        "watch_instructions": "New front-page submissions (a high-churn demo feed).",
        "fetch_strategy": FetchStrategy.API,
        "check_interval_minutes": 60,
    },
    {
        "name": "GitHub Status — incident history",
        "url": "https://www.githubstatus.com/history.rss",
        "vertical": Vertical.STATUS,
        "watch_instructions": "New incidents or maintenance windows.",
        "fetch_strategy": FetchStrategy.API,
        "check_interval_minutes": 180,
    },
    {
        "name": "Python PEPs — index",
        "url": "https://peps.python.org/api/peps.json",
        "vertical": Vertical.DOCS,
        "watch_instructions": "New or updated Python Enhancement Proposals.",
        "fetch_strategy": FetchStrategy.API,
        "check_interval_minutes": 720,
    },
    {
        "name": "Example.com (stable control)",
        "url": "https://example.com/",
        "vertical": Vertical.GENERIC,
        "watch_instructions": "A static page; should never raise a meaningful change.",
        "fetch_strategy": FetchStrategy.AUTO,
        "check_interval_minutes": 1440,
    },
]


class Command(BaseCommand):
    help = "Seed monitoring-friendly demo watch targets (idempotent)."

    def handle(self, *args, **options):
        created = 0
        for spec in DEMO_TARGETS:
            _, was_created = WatchTarget.objects.get_or_create(url=spec["url"], defaults=spec)
            created += int(was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded demo targets: {created} created, "
                f"{len(DEMO_TARGETS) - created} already present "
                f"({WatchTarget.objects.count()} total)."
            )
        )
