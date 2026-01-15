"""Small retry-with-backoff helper for transient failures."""

from __future__ import annotations

import time
from collections.abc import Callable


def retry_call[T](
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.1,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``fn`` up to ``attempts`` times with exponential backoff.

    Re-raises the last exception if every attempt fails. ``sleep`` is injectable
    so tests/metrics can run without real delays.
    """
    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except exceptions as exc:
            last_exc = exc
            if i < attempts - 1:
                sleep(base_delay * (2**i))
    assert last_exc is not None
    raise last_exc
