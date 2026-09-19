"""In-memory rate limiting for the /ai/* routes.  OWNER: backend engineer.

Per-key fixed-window counter, no external dependency (no Redis, no slowapi)
-- fine for a single-process prototype. If this ever runs as multiple
processes or replicas, each gets its own counter and the effective limit
multiplies by however many processes are running; swap this for a shared
store (Redis) before that happens.

`check()` is called directly inside each /ai/* route rather than wired up
as a FastAPI dependency, because the "key" to rate-limit on differs per
route (some routes have a student_id in the body, some don't) -- see
deps.ai_rate_limit_key for how the key is chosen.
"""
import time
from collections import defaultdict

from fastapi import HTTPException

from ..config import AI_RATE_LIMIT, AI_RATE_LIMIT_WINDOW_SECONDS

_hits: dict[str, list[float]] = defaultdict(list)


def check(key: str) -> None:
    now = time.time()
    window_start = now - AI_RATE_LIMIT_WINDOW_SECONDS
    hits = _hits[key]
    while hits and hits[0] < window_start:
        hits.pop(0)
    if len(hits) >= AI_RATE_LIMIT:
        raise HTTPException(
            429,
            f'AI request limit reached ({AI_RATE_LIMIT} per '
            f'{AI_RATE_LIMIT_WINDOW_SECONDS // 60} minutes). Try again shortly.',
        )
    hits.append(now)
