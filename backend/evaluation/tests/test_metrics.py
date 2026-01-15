"""Assert the §9 metrics meet their targets. Pure functions — no DB needed."""

from evaluation import metrics


def test_false_positive_reduction_is_substantial():
    r = metrics.false_positive_reduction()
    # Naive flags essentially all cosmetic churn.
    assert r["naive_false_positive_rate"] > 0.9
    # Semantic suppresses most of it...
    assert r["semantic_false_positive_rate"] < r["naive_false_positive_rate"]
    # ...for a large reduction (target ~60-70%).
    assert r["false_positive_reduction"] >= 0.5
    # ...without dropping the real changes.
    assert r["semantic_recall"] >= 0.9


def test_extraction_accuracy_meets_target():
    r = metrics.extraction_accuracy()
    assert r["accuracy"] >= 0.9


def test_cost_reduction_is_significant():
    r = metrics.cost_reduction()
    assert r["optimized_usd"] < r["baseline_usd"]
    assert r["cost_reduction"] >= 0.5


def test_latency_scales():
    r = metrics.latency(n=500)
    assert r["pages"] == 500
    assert r["p50_ms"] <= r["p95_ms"]
    # Generous bound to stay stable across CI machines.
    assert r["p95_ms"] < 2000


def test_reliability_improves_with_retry():
    r = metrics.reliability()
    assert r["with_retry_success"] > r["single_attempt_success"]
    assert r["with_retry_success"] >= 0.9
