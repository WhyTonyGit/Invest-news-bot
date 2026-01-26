from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque


class HourlyRateLimiter:
    def __init__(self, max_per_hour: int) -> None:
        self.max_per_hour = max_per_hour
        self._events: dict[int, Deque[datetime]] = defaultdict(deque)

    def allow(self, tg_id: int, now: datetime | None = None) -> bool:
        if now is None:
            now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=1)
        queue = self._events[tg_id]
        while queue and queue[0] < window_start:
            queue.popleft()
        if len(queue) >= self.max_per_hour:
            return False
        queue.append(now)
        return True
