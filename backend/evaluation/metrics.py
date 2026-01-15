"""Compute the §9 metrics from the labelled datasets + modeled scenarios.

All metrics run without network or an LLM key, so they are reproducible. Where
a metric is modeled (cost), the assumptions are explicit in the result.
"""

from __future__ import annotations

import random
import time

from django.conf import settings

from core.retry import retry_call
from llm.pricing import estimate_cost
from monitoring.diff.naive import diff_text
from monitoring.diff.semantic import classify
from monitoring.extract import rules
from monitoring.extract.schema import coerce

from .datasets import change_cases, extraction_cases


def false_positive_reduction(cases: list[dict] | None = None) -> dict:
    cases = cases or change_cases()
    noise = [c for c in cases if c["label"] == "noise"]
    meaningful = [c for c in cases if c["label"] == "meaningful"]

    def naive_positive(c: dict) -> bool:
        return diff_text(c["prev_text"], c["cur_text"]).changed

    def semantic_positive(c: dict) -> bool:
        return classify(c["prev_text"], c["cur_text"], c["prev_fields"], c["cur_fields"]).meaningful

    naive_fp = sum(naive_positive(c) for c in noise)
    sem_fp = sum(semantic_positive(c) for c in noise)
    naive_fp_rate = naive_fp / len(noise)
    sem_fp_rate = sem_fp / len(noise)
    reduction = (naive_fp_rate - sem_fp_rate) / naive_fp_rate if naive_fp_rate else 0.0

    # Recall on meaningful changes (we must not suppress the real ones).
    naive_recall = sum(naive_positive(c) for c in meaningful) / len(meaningful)
    sem_recall = sum(semantic_positive(c) for c in meaningful) / len(meaningful)

    return {
        "noise_cases": len(noise),
        "meaningful_cases": len(meaningful),
        "naive_false_positive_rate": round(naive_fp_rate, 4),
        "semantic_false_positive_rate": round(sem_fp_rate, 4),
        "false_positive_reduction": round(reduction, 4),
        "naive_recall": round(naive_recall, 4),
        "semantic_recall": round(sem_recall, 4),
    }


def extraction_accuracy(cases: list[dict] | None = None) -> dict:
    cases = cases or extraction_cases()
    total = correct = 0
    for c in cases:
        extracted = rules.rule_extract(c["content"], c["schema"])
        for field, expected in c["expected"].items():
            total += 1
            got = coerce(extracted.get(field), c["schema"][field])
            if got == expected:
                correct += 1
    return {
        "fields_evaluated": total,
        "fields_correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
    }


def cost_reduction(
    pages: int = 100, unchanged_frac: float = 0.6, meaningful_frac: float = 0.2
) -> dict:
    """Modeled per-page LLM cost: skip-unchanged + cheap-vs-strong routing.

    Token assumptions are explicit; the metric is the relative reduction.
    """
    extract_tokens = (1500, 200)  # (prompt, completion)
    assess_tokens = (800, 150)
    strong = settings.LLM_MODEL_ASSESS
    cheap = settings.LLM_MODEL_EXTRACT

    # Baseline: extract + assess every page on the strong model, no skipping.
    per_page_baseline = estimate_cost(strong, *extract_tokens) + estimate_cost(
        strong, *assess_tokens
    )
    baseline = pages * per_page_baseline

    # Optimized: skip unchanged pages entirely; extract on the cheap model;
    # assess only the pages with a meaningful change.
    checked = pages * (1 - unchanged_frac)
    optimized = checked * estimate_cost(cheap, *extract_tokens) + (
        pages * meaningful_frac
    ) * estimate_cost(strong, *assess_tokens)
    reduction = (baseline - optimized) / baseline if baseline else 0.0
    return {
        "pages": pages,
        "unchanged_fraction": unchanged_frac,
        "meaningful_fraction": meaningful_frac,
        "baseline_usd": round(baseline, 6),
        "optimized_usd": round(optimized, 6),
        "cost_reduction": round(reduction, 4),
        "assumptions": {"extract_tokens": extract_tokens, "assess_tokens": assess_tokens},
    }


def latency(n: int = 500, seed: int = 7) -> dict:
    """p50/p95 of the local intelligence layer (extract + semantic diff).

    Network fetch and LLM calls are excluded — this measures the CPU-bound
    processing per page.
    """
    rng = random.Random(seed)
    filler = " ".join(["lorem ipsum dolor sit amet consectetur"] * 40)
    schema = {"price": "number", "in_stock": "boolean"}
    durations: list[float] = []
    for i in range(n):
        old_price = rng.randint(100, 9999)
        new_price = old_price + rng.choice([0, 0, 0, 50, -25])
        prev = f"{filler} Price {old_price}. In stock. Updated 2024-01-01 10:00:00."
        cur = f"{filler} Price {new_price}. In stock. Updated 2025-02-0{i % 9} 11:00:00."
        start = time.perf_counter()
        rules.rule_extract(cur, schema)
        classify(prev, cur, {"price": old_price}, {"price": new_price})
        durations.append((time.perf_counter() - start) * 1000)

    durations.sort()
    return {
        "pages": n,
        "p50_ms": round(durations[int(0.50 * n)], 3),
        "p95_ms": round(durations[int(0.95 * n)], 3),
        "mean_ms": round(sum(durations) / n, 3),
    }


def reliability(
    trials: int = 500, fail_prob: float = 0.4, attempts: int = 3, seed: int = 1234
) -> dict:
    """Eventual success rate with retry-with-backoff under transient failures."""

    def measure(max_attempts: int) -> float:
        rng = random.Random(seed)

        def flaky() -> str:
            if rng.random() < fail_prob:
                raise RuntimeError("transient")
            return "ok"

        ok = 0
        for _ in range(trials):
            try:
                retry_call(flaky, attempts=max_attempts, base_delay=0.0, sleep=lambda _: None)
                ok += 1
            except RuntimeError:
                pass
        return ok / trials

    single = measure(1)
    retried = measure(attempts)
    return {
        "trials": trials,
        "transient_fail_prob": fail_prob,
        "attempts": attempts,
        "single_attempt_success": round(single, 4),
        "with_retry_success": round(retried, 4),
    }


def run_all() -> dict:
    return {
        "false_positive_reduction": false_positive_reduction(),
        "extraction_accuracy": extraction_accuracy(),
        "cost_reduction": cost_reduction(),
        "latency": latency(),
        "reliability": reliability(),
    }
