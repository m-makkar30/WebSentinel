import json

from django.core.management.base import BaseCommand

from evaluation import metrics


class Command(BaseCommand):
    help = "Run the evaluation harness and print the §9 metrics."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Emit raw JSON only.")

    def handle(self, *args, **options):
        results = metrics.run_all()

        if options["json"]:
            self.stdout.write(json.dumps(results, indent=2))
            return

        fp = results["false_positive_reduction"]
        ex = results["extraction_accuracy"]
        cost = results["cost_reduction"]
        lat = results["latency"]
        rel = results["reliability"]

        out = self.stdout
        out.write(self.style.MIGRATE_HEADING("WebSentinel — evaluation metrics\n"))

        out.write("False-positive reduction (semantic vs naive)")
        out.write(
            f"  noise={fp['noise_cases']} meaningful={fp['meaningful_cases']} | "
            f"naive FP={fp['naive_false_positive_rate']:.0%} -> "
            f"semantic FP={fp['semantic_false_positive_rate']:.0%}"
        )
        out.write(
            self.style.SUCCESS(
                f"  => {fp['false_positive_reduction']:.0%} fewer false positives "
                f"(semantic recall {fp['semantic_recall']:.0%})\n"
            )
        )

        out.write("Extraction accuracy (rule-based, reproducible)")
        out.write(
            self.style.SUCCESS(
                f"  => {ex['accuracy']:.0%} ({ex['fields_correct']}/{ex['fields_evaluated']} fields)\n"
            )
        )

        out.write("LLM cost reduction (modeled: skip-unchanged + model routing)")
        out.write(
            f"  baseline=${cost['baseline_usd']:.4f} -> optimized=${cost['optimized_usd']:.4f}"
        )
        out.write(
            self.style.SUCCESS(f"  => {cost['cost_reduction']:.0%} lower cost per check cycle\n")
        )

        out.write("Throughput / latency (local intelligence layer)")
        out.write(
            self.style.SUCCESS(
                f"  => {lat['pages']} pages: p50={lat['p50_ms']}ms p95={lat['p95_ms']}ms\n"
            )
        )

        out.write("Reliability (retry-with-backoff)")
        out.write(
            self.style.SUCCESS(
                f"  => {rel['single_attempt_success']:.0%} single-attempt -> "
                f"{rel['with_retry_success']:.0%} with {rel['attempts']} attempts\n"
            )
        )
