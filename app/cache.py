"""Redis: caches code->URL lookups (the hot redirect path) and enforces a
fixed-window rate limit on link creation. Degrades gracefully to no-op if Redis
is not configured (so unit tests run without it)."""
import os

import redis

REDIS_URL = os.environ.get("REDIS_URL")
_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None


def cache_get(code: str) -> str | None:
    if _client is None:
        return None
    return _client.get(f"url:{code}")


def cache_set(code: str, url: str, ttl: int = 3600) -> None:
    if _client is not None:
        _client.set(f"url:{code}", url, ex=ttl)


def rate_limit_ok(key: str, limit: int, window: int = 60) -> bool:
    """Fixed-window counter: allow `limit` actions per `window` seconds per key."""
    if _client is None:
        return True
    redis_key = f"rl:{key}"
    count = _client.incr(redis_key)
    if count == 1:
        _client.expire(redis_key, window)
    return count <= limit
