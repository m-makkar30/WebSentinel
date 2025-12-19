# WebSentinel

**Web change-intelligence platform** — watches the web pages that matter to a
business and reports, in plain language, _only_ when something important
actually changes.

> 🚧 **Status: under active construction.** This repository is being built
> commit-by-commit against a defined roadmap. Core services land in subsequent
> commits; see the roadmap below.

## What it does

You register _watch targets_ (a URL plus what you care about on it). A background
fleet of workers periodically renders those pages, extracts the relevant
structured data, and detects **semantically meaningful** changes — not raw HTML
noise. It then assesses how significant each change is, explains what changed and
why it matters, and surfaces alerts and trends in a dashboard.

The hard problem — and the differentiator — is **noise suppression**: telling a
real change (a price moved ₹1,299 → ₹999, a new data-retention clause appeared)
apart from cosmetic churn (rotating ads, footer dates, session IDs).

## Tech stack

| Layer              | Technology                                    |
| ------------------ | --------------------------------------------- |
| Backend            | Django + Django REST Framework                |
| Async / scheduling | Celery + Celery Beat (Redis broker)           |
| Database           | PostgreSQL + pgvector                         |
| Browser automation | Playwright (Python)                           |
| LLM                | NVIDIA NIM (OpenAI-compatible API)            |
| Frontend           | React + Vite + TypeScript + Tailwind + shadcn |
| Packaging          | Docker + Docker Compose                       |

## Repository layout

| Path        | Purpose                                                            |
| ----------- | ------------------------------------------------------------------ |
| `backend/`  | Django project, DRF API, Celery workers, fetch/extract/diff/assess |
| `frontend/` | React + Vite + TypeScript dashboard (scaffolded later)             |
| `docker/`   | Dockerfiles and compose-related assets                             |
| `docs/`     | Architecture notes and ADRs (`docs/adr/`)                          |

## Getting started

A one-command bring-up (`docker compose up`) lands in a later commit. For now the
repo carries project tooling and structure.

### Developer tooling

This repo uses [pre-commit](https://pre-commit.com/) to run linters/formatters:

- **Python** — [ruff](https://docs.astral.sh/ruff/) (lint) + [black](https://black.readthedocs.io/) (format)
- **Web / docs** — [prettier](https://prettier.io/) (eslint is wired in once the
  frontend is scaffolded)

```bash
uv tool install pre-commit   # or: pipx install pre-commit
pre-commit install           # enable hooks on commit
pre-commit run --all-files   # run them across the repo
```

## Roadmap

The build follows ~22 progressive commits:

1. Scaffold + tooling **(this commit)**
2. Docker Compose: Postgres (pgvector) + Redis
3. Django + DRF, env-based settings, `/healthz`
4. Core models — targets, snapshots, changes, alerts
5. Target CRUD API + OpenAPI docs
6. Celery + Beat heartbeat
7. Playwright rendering worker
8. Polite fetching (API-first, robots, block detection)
9. NVIDIA NIM client (provider interface, cost logging)
10. Structured extraction
11. Naive change detection (baseline)
12. Semantic change detection (field diff + embeddings)
13. LLM impact assessment + severity + alerts
14. Per-target scheduling, content-hash skip, dedup
15. Frontend shell
16. Watch-target management UI
17. Change timeline + before/after diff viewer
18. Dashboard (alerts, trends, cost panel)
19. Evaluation harness + labelled dataset
20. Live demo seed + runner
21. Structured logging + resilience
22. Docs, architecture, metrics, screenshots

## License

[MIT](LICENSE).
