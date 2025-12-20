# WebSentinel backend image (Django + DRF).
# Build context is ./backend (see docker-compose.yml).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg[binary] bundles its own libpq, so no system packages are needed here.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Default command; compose overrides this to run migrations first in dev.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
