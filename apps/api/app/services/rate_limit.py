import time
from collections import defaultdict

from fastapi import HTTPException

# Single-process, in-memory fixed-window limiter. Deliberately simple: this
# app runs as one instance (see the project plan's scope notes on avoiding
# distributed infrastructure a single-tenant internal tool doesn't need) —
# a multi-replica deployment would need a shared store (e.g. Redis) instead.
_window_start: dict[str, float] = defaultdict(float)
_window_count: dict[str, int] = defaultdict(int)


def check_rate_limit(key: str, max_requests: int, window_seconds: float) -> None:
    now = time.monotonic()
    if now - _window_start[key] >= window_seconds:
        _window_start[key] = now
        _window_count[key] = 0

    _window_count[key] += 1
    if _window_count[key] > max_requests:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: at most {max_requests} requests per "
            f"{window_seconds:.0f}s for '{key}'",
        )
