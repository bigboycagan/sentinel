"""Minimal in-process sliding-window rate limiter (no external dependencies).

Suitable for the single-process v1 deployment; a Redis-backed limiter would
replace `allow()` behind the same interface at scale.
"""

import os
import time
from collections import defaultdict, deque

_window_seconds = 60.0
_max_events = int(os.environ.get("ANALYSIS_RATE_LIMIT_PER_MIN", "30"))

_events: dict[str, deque[float]] = defaultdict(deque)


def allow(key: str) -> bool:
    """Return True if `key` may perform another event within the window."""
    now = time.monotonic()
    bucket = _events[key]
    while bucket and now - bucket[0] > _window_seconds:
        bucket.popleft()
    if len(bucket) >= _max_events:
        return False
    bucket.append(now)
    return True
