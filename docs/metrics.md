# Metrics & methodology

Every metric is computed by the evaluation harness (`backend/evaluation/`) and
is **reproducible with one command, no network or API key required**:

```bash
make eval                      # human-readable report
docker compose exec backend python manage.py run_eval --json   # raw JSON
cd backend && pytest           # the same metrics asserted against targets
```

The harness uses a hand-labelled dataset (`evaluation/datasets.py`) plus modeled
scenarios (`evaluation/metrics.py`). Numbers below are from a representative run;
re-run to regenerate.

## 1. False-positive reduction — semantic vs naive

**Method.** ~126 labelled snapshot pairs, each `meaningful` or `noise`:

- _easy noise_ — date/time/year/session-id and whitespace churn around
  identical content;
- _hard noise_ — rotating banners and reordered/reworded boilerplate with low
  text similarity (only embeddings can suppress these, so without an LLM key
  they remain semantic false positives — included on purpose);
- _meaningful_ — price/availability field changes and substantial clause
  rewrites.

The **naive** detector flags any textual difference (so every case is a
positive). The **semantic** detector uses field diffs + normalized text +
embedding similarity. We report the false-positive rate on the noise cases and
recall on the meaningful cases.

**Result:** naive FP **99%** → semantic FP **26%** ⇒ **~74% fewer false
positives**, while semantic **recall stays at 100%** (no real change dropped).

## 2. Extraction accuracy

**Method.** 80 labelled fields (price + availability) across currencies (₹, $,
€, £, Rs, USD) and stock phrasings; the rule-based extractors run with type
coercion, compared field-by-field to expected values. Reproducible without an
LLM. (Prose/clause fields require the LLM and are evaluated when configured.)

**Result:** **100%** on rule-extractable fields.

## 3. LLM cost reduction

**Method (modeled, explicit assumptions).** Per check cycle of N pages:

- _baseline_ — extract **and** assess every page on the strong model, no
  skipping;
- _optimized_ — skip unchanged pages by content hash, extract on the cheap
  model, and assess only pages with a meaningful change.

Token assumptions: extraction ≈ 1500 prompt / 200 completion; assessment ≈ 800 /
150. Rates from `llm/pricing.py`. The metric is the **relative** reduction, so
absolute rates matter less than consistency.

**Result:** **~89%** lower cost per check cycle (at 60% unchanged, 20%
meaningful).

## 4. Throughput / latency at scale

**Method.** The local intelligence layer (rule extraction + semantic diff) over
**500 synthetic pages**; network fetch and LLM calls are excluded so this
measures CPU-bound processing.

**Result:** **p50 ≈ 0.5ms, p95 ≈ 1.3ms** per page — the detection layer is not
the bottleneck; fetch latency dominates real end-to-end time.

## 5. Reliability

**Method.** A flaky operation failing with probability 0.4 per attempt, wrapped
in retry-with-backoff (`core/retry.py`), over 500 trials; single attempt vs 3
attempts.

**Result:** **62% → 94%** eventual success with 3 attempts.

---

These are demonstrative engineering metrics for a local project, not
production-SLA claims. The point is that each number is defensible and
regenerable from code.
