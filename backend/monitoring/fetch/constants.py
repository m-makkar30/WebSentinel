"""Shared fetch constants: one honest, consistent identity across HTTP + browser."""

# A normal Chrome UA with a WebSentinel token so site owners can identify the
# monitor in their logs. Used by both the httpx client and the Playwright context.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 WebSentinel/0.1 (+monitoring)"
)

# Short product token matched against robots.txt User-agent groups.
ROBOTS_UA_TOKEN = "WebSentinel"

HTTP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9," "application/json;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

HTTP_TIMEOUT = 20.0  # seconds
# Monitoring is low-frequency by design; pace requests to the same host.
MIN_REQUEST_INTERVAL = 2.0  # seconds
