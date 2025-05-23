import os
import json
from cachetools import TTLCache
from cachetools import cached
try:
    import redis
except ImportError:
    redis = None

# In-memory cache
memory_cache = TTLCache(maxsize=1000, ttl=600)


def cache_decorator(ttl_seconds: int = 600, maxsize: int = 1000):
    custom = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
    return cached(custom)

class RedisCache:
    def __init__(self, namespace: str = "f1", ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self.namespace = namespace
        self.client = None
        url = os.getenv("REDIS_URL")
        if redis and url:
            self.client = redis.from_url(url)

    def _make_key(self, path, params):
        ps = ":".join(f"{k}={v}" for k,v in sorted(params.items()))
        return f"{self.namespace}:{path}:{ps}"

    def get(self, path, params):
        if not self.client:
            return None
        data = self.client.get(self._make_key(path, params))
        return json.loads(data) if data else None

    def set(self, path, params, value):
        if not self.client:
            return
        key = self._make_key(path, params)
        self.client.setex(key, self.ttl, json.dumps(value))

redis_cache = RedisCache()


def fetch_with_cache(fetch_fn, path: str, **params):
    # Redis first
    data = redis_cache.get(path, params)
    if data is not None:
        return data
    # In-memory fallback
    key = f"{path}:{tuple(sorted(params.items()))}"
    if key in memory_cache:
        return memory_cache[key]
    # Fetch and store
    data = fetch_fn(path, **params)
    memory_cache[key] = data
    redis_cache.set(path, params, data)
    return data