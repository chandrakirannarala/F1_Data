import os
import json
from cachetools import TTLCache
from cachetools import cached

# Optional Redis support
try:
    import redis
except ImportError:
    redis = None

# In-memory TTL cache: holds up to 1000 entries for 600 seconds by default
memory_cache = TTLCache(maxsize=1000, ttl=600)


def cache_decorator(ttl_seconds: int = 600, maxsize: int = 1000):
    """
    Returns a cachetools TTLCache decorator with custom TTL and size.
    """
    custom_cache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
    return cached(custom_cache)


class RedisCache:
    """
    Wrapper for Redis-based caching. Falls back silently if Redis is unavailable.
    """
    def __init__(self, namespace: str = "f1", ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self.namespace = namespace
        self.client = None
        redis_url = os.getenv("REDIS_URL")
        if redis and redis_url:
            self.client = redis.from_url(redis_url)

    def _make_key(self, path: str, params: dict) -> str:
        param_str = ":".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{self.namespace}:{path}:{param_str}"

    def get(self, path: str, params: dict):
        if not self.client:
            return None
        key = self._make_key(path, params)
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None

    def set(self, path: str, params: dict, value):
        if not self.client:
            return
        key = self._make_key(path, params)
        self.client.setex(key, self.ttl, json.dumps(value))


# Singleton instance
redis_cache = RedisCache(ttl_seconds=600)


def fetch_with_cache(fetch_fn, path: str, **params):
    """
    First tries Redis cache, then in-memory cache, then fetches via fetch_fn
    (e.g., api.fetch_json), and stores in both caches.
    """
    # Try Redis first
    data = redis_cache.get(path, params)
    if data is not None:
        return data

    # Fallback to in-memory cache key
    cache_key = f"{path}:{tuple(sorted(params.items()))}"
    if cache_key in memory_cache:
        return memory_cache[cache_key]

    # Actual fetch
    data = fetch_fn(path, **params)

    # Populate caches
    memory_cache[cache_key] = data
    redis_cache.set(path, params, data)

    return data
