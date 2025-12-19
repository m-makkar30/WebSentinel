# docker

Dockerfiles and Compose-related assets for WebSentinel.

The full stack (Postgres + pgvector, Redis, Django API, Celery worker + beat,
Playwright fetch worker, frontend) is brought up with a single
`docker compose up` from the repository root. Services are added incrementally
across the roadmap.
