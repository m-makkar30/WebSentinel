import time

from django.core.management import call_command
from django.core.management.base import BaseCommand

from monitoring.models import Alert, Change, Snapshot, WatchTarget
from monitoring.pipeline import process_target


class Command(BaseCommand):
    help = "Seed demo targets and run real checks against them (one-command demo)."

    def add_arguments(self, parser):
        parser.add_argument("--no-seed", action="store_true", help="Skip seeding.")
        parser.add_argument("--no-poll", action="store_true", help="Skip the live-detection poll.")
        parser.add_argument("--poll-attempts", type=int, default=6)
        parser.add_argument("--poll-seconds", type=int, default=20)

    def handle(self, *args, **options):
        if not options["no_seed"]:
            call_command("seed_demo")

        targets = list(WatchTarget.objects.all())
        out = self.stdout

        out.write(self.style.MIGRATE_HEADING("\nBaseline check (real fetches)"))
        for target in targets:
            result = process_target(target)
            self._report(target, result)

        if not options["no_poll"]:
            out.write(
                self.style.MIGRATE_HEADING(
                    f"\nPolling for a real change "
                    f"(up to {options['poll_attempts']}x{options['poll_seconds']}s)"
                )
            )
            detected = False
            for attempt in range(options["poll_attempts"]):
                time.sleep(options["poll_seconds"])
                before = Change.objects.count()
                for target in targets:
                    process_target(target)
                new_changes = Change.objects.count() - before
                out.write(f"  attempt {attempt + 1}: {new_changes} new change(s)")
                if new_changes:
                    detected = True
                    break
            if not detected:
                out.write(
                    "  no live change yet — watched pages drift over hours/days; "
                    "Beat will keep checking on each target's schedule."
                )

        out.write(self.style.MIGRATE_HEADING("\nSummary"))
        out.write(f"  targets:   {WatchTarget.objects.count()}")
        out.write(f"  snapshots: {Snapshot.objects.count()}")
        out.write(
            f"  changes:   {Change.objects.count()} "
            f"({Change.objects.filter(is_meaningful=True).count()} meaningful)"
        )
        out.write(f"  alerts:    {Alert.objects.count()}")
        out.write(self.style.SUCCESS("\nOpen the dashboard at http://localhost:5173 to explore.\n"))

    def _report(self, target, result):
        if result.get("skipped"):
            self.stdout.write(f"  · {target.name}: unchanged (skipped)")
            return
        flag = "blocked" if result["blocked"] else ("ok" if result["ok"] else "error")
        change = " · CHANGE" if result.get("change_id") else ""
        self.stdout.write(
            f"  · {target.name}: {flag} via {result['method']} "
            f"(HTTP {result['http_status']}, {result['content_chars']} chars){change}"
        )
