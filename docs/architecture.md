# Architecture

WebSentinel is a Django + Celery backend, a Playwright fetch worker, a React
dashboard, Postgres (pgvector) and Redis — all orchestrated by Docker Compose.

## Components

| Service        | Role                                                                 |
| -------------- | -------------------------------------------------------------------- |
| `backend`      | Django + DRF API, admin, migrations, management commands             |
| `worker`       | Celery worker (default queue) — runs the dispatcher                  |
| `beat`         | Celery Beat — schedules the per-target dispatcher + heartbeat        |
| `fetch-worker` | Celery worker (`fetch` queue) with Chromium/Playwright               |
| `frontend`     | Vite dev server (React) proxying `/api` to the backend               |
| `postgres`     | PostgreSQL with the `pgvector` extension (snapshot embeddings)       |
| `redis`        | Celery broker + result backend                                       |

## Data model

```
WatchTarget ──< Snapshot ──< Change ──< Alert
     │                          (prev/current snapshot FKs)
     ├──< CheckRun (run history)
     └──< LLMUsage (token + cost accounting; in the llm app)
```

- **WatchTarget** — URL + what to watch (`vertical`, `watch_instructions`,
  `extraction_schema`, `fetch_strategy`, `check_interval_minutes`, `status`).
  Addressed by `uuid` in the API.
- **Snapshot** — one fetch: raw + normalized text, `content_hash`, extracted
  fields, `embedding` (pgvector `VectorField(1024)`), screenshot, fetch metadata.
- **Change** — a detected diff between two snapshots: `detection_method`,
  `change_type`, `is_meaningful`, `severity`, `significance_score`, `summary`,
  `why_it_matters`, `field_diffs`, `text_diff`, `dedup_hash`.
- **Alert** — surfaced notification (kind/level/status), usually tied to a
  meaningful Change; also informational (blocked/error).
- **CheckRun** — one pipeline execution (status/method/http/duration/error).
- **LLMUsage** — per-call tokens + estimated cost (powers the cost panel).

## The check pipeline

`monitoring/pipeline.py::process_target` is shared by the Celery task and the
demo runner:

```
fetch_target (robots → API/feed-first HTTP → escalate to browser if JS-rendered)
   → block/error handling (mark target, alert)
   → content-hash skip  ── unchanged ──▶ stop (no snapshot, no LLM)
   → persist Snapshot
   → extract (rules first, LLM for the rest)
   → semantic diff (field diff + normalized text + embedding cosine)
   → assess (LLM severity + why-it-matters → Alert)   [only if meaningful]
   → record CheckRun
```

### Scheduling

Beat runs `dispatch_due_checks` on a fixed interval; it enqueues `check_target`
for active targets whose last check is older than their own
`check_interval_minutes` (per-target cadence without a periodic-task row per
target). Fetch/render tasks run on a dedicated `fetch` queue so browser work
doesn't block lighter tasks.

### Noise suppression (the differentiator)

1. **Structured field diff** — a change in an extracted field (price, stock,
   clause) is meaningful regardless of surrounding HTML noise.
2. **Text normalization** — dates, times, years, and session/long IDs are
   stripped, so rotating footers/timestamps collapse to identical. This makes
   suppression work _without_ an LLM (keeping the metric reproducible).
3. **Embedding cosine similarity** (pgvector) — when NVIDIA NIM is configured,
   high embedding similarity suppresses reworded-but-same-meaning prose that
   text diffing alone would flag.

The naive detector (any text diff = a change) is retained as the baseline the
semantic detector is measured against (see [metrics.md](metrics.md)).

## LLM provider

`llm/` wraps NVIDIA NIM behind a thin provider interface (OpenAI-compatible
client). Model routing sends routine extraction to a cheap model
(`LLM_MODEL_EXTRACT`) and impact assessment to a stronger one
(`LLM_MODEL_ASSESS`); `max_tokens` is always set; retries/timeouts are handled
by the client; every call's tokens + estimated cost are recorded as `LLMUsage`.
Unset key → graceful rule-based fallback.

## Resilience

- Transient HTTP transport/timeout errors are retried with exponential backoff
  (`core/retry.py`).
- Each stage is guarded so a failure is logged and recorded on the `CheckRun`
  rather than crashing the worker; the target's status/`status_note` surface in
  the UI (badge + banner + run-history dots).
- Structured, leveled logging across the app loggers.
