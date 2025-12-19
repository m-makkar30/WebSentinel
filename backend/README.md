# backend

Django + Django REST Framework service for WebSentinel.

Houses the API, data models, and the Celery workers that fetch pages
(Playwright / API-first), extract structured content, detect semantic changes,
and assess impact via the NVIDIA NIM LLM client.

Initialized in a later commit (see the roadmap in the root `README.md`).
