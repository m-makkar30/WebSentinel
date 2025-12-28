# WebSentinel Playwright fetch worker.
# Separate from the backend image because the browser + its OS deps are heavy
# and only this worker needs them. Build context is ./backend.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

# Download Chromium and its system dependencies (matched to the installed
# Playwright version). --with-deps installs the required apt packages.
RUN playwright install --with-deps chromium

COPY . .

# Consumes the dedicated `fetch` queue.
CMD ["celery", "-A", "websentinel", "worker", "-l", "info", "-Q", "fetch", "-n", "fetch@%h", "--concurrency=2"]
