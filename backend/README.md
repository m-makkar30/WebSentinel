# backend

Django + Django REST Framework service for WebSentinel.

Houses the API, data models, and the Celery workers that fetch pages
(Playwright / API-first), extract structured content, detect semantic changes,
and assess impact via the NVIDIA NIM LLM client.

## Layout

- `websentinel/` — project config (12-factor settings, urls, wsgi/asgi)
- `core/` — shared app; currently the `/healthz` probe
- `requirements.txt` — runtime deps; `pyproject.toml` — ruff/black config

## Run

Brought up by the root `docker compose up` (service `backend`, port 8000). The
container runs migrations then `runserver`; `GET /healthz` reports DB health.
Local non-Docker runs read a repo-root `.env` automatically.
