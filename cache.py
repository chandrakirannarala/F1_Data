import os
import json
import hashlib
from cachetools import TTLCache
from cachetools import cached
from typing import Any, Dict, Optional
try:
    import redis
except ImportError:
    redis = None

# In-memory cache with different TTL for different data types
memory_cache = TTLCache(maxsize=1000, ttl=600)  # 10 minutes default

# Different cache strategies for different data types
CACHE_SETTINGS = {
    "meetings": {"ttl": 3600 * 24, "maxsize": 100},      # 24 hours - meetings don't change often
    "sessions": {"ttl": 3600 * 12, "maxsize": 500},      # 12 hours - sessions are relatively static
    "drivers": {"ttl": 3600 * 6, "maxsize": 1000},       # 6 hours - driver info can change
    "laps": {"ttl": 600, "maxsize": 5000},               # 10 minutes - lap data updates frequently
    "stints": {"ttl": 1200, "maxsize": 2000},            # 20 minutes - stint data
    "pit": {"ttl": 1200, "maxsize": 1000},               # 20 minutes - pit data
    "car_data": {"ttl": 300, "maxsize": 10000},          # 5 minutes - telemetry data changes rapidly
    "position": {"ttl": 300, "maxsize": 5000},           # 5 minutes - position data
    "weather": {"ttl": 1800, "maxsize": 500},            # 30 minutes - weather changes slowly
    "race_control": {"ttl": 600, "maxsize": 1000},       # 10 minutes - race control messages
}


def get_cache_settings(endpoint: str) -> Dict[str, int]:
    """Get cache settings for a specific API endpoint."""
    return CACHE_SETTINGS.get(endpoint, {"ttl": 600, "maxsize": 1000})


def cache_decorator(endpoint: str):
    """Create a cache decorator with endpoint-specific settings."""
    settings = get_cache_settings(endpoint)
    custom_cache = TTLCache(maxsize=settings["maxsize"], ttl=settings["ttl"])
    return cached(custom_cache)


class RedisCache:
    def __init__(self, namespace: str = "f1"):
        self.namespace = namespace
        self.client = None
        url = os.getenv("REDIS_URL")
        if redis and url:
            try:
                self.client = redis.from_url(url, decode_responses=True)
                # Test connection
                self.client.ping()
                print("✓ Redis connection established")
            except Exception as e:
                print(f"⚠ Redis connection failed: {e}")
                self.client = None
        else:
            print("⚠ Redis not available, using in-memory cache only")

    def _make_key(self, path: str, params: Dict[str, Any]) -> str:
        """Create a unique cache key from path and parameters."""
        # Sort parameters for consistent key generation
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        key_str = f"{path}?{param_str}" if param_str else path
        
        # Hash long keys to avoid Redis key length limits
        if len(key_str) > 200:
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            return f"{self.namespace}:hash:{key_hash}"
        
        return f"{self.namespace}:{key_str}"

    def get(self, path: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached data from Redis."""
        if not self.client:
            return None
        
        try:
            key = self._make_key(path, params)
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None

    def set(self, path: str, params: Dict[str, Any], value: Any) -> None:
        """Store data in Redis with appropriate TTL."""
        if not self.client:
            return
        
        try:
            key = self._make_key(path, params)
            settings = get_cache_settings(path)
            ttl = settings["ttl"]
            
            self.client.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            print(f"Redis set error: {e}")

    def clear_pattern(self, pattern: str) -> int:
        """Clear cache keys matching a pattern."""
        if not self.client:
            return 0
        
        try:
            keys = self.client.keys(f"{self.namespace}:{pattern}")
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis clear error: {e}")
            return 0


# Global Redis cache instance
redis_cache = RedisCache()


def fetch_with_cache(fetch_fn, path: str, **params):
    """
    Fetch data with multi-level caching strategy:
    1. Try Redis cache first (if available)
    2. Fall back to in-memory cache
    3. Finally fetch from API and cache the result
    """
    # Try Redis first
    data = redis_cache.get(path, params)
    if data is not None:
        return data
    
    # Try in-memory cache
    key = f"{path}:{hash(tuple(sorted(params.items())))}"
    if key in memory_cache:
        return memory_cache[key]
    
    # Fetch from API
    try:
        data = fetch_fn(path, **params)
        
        # Store in both caches
        memory_cache[key] = data
        redis_cache.set(path, params, data)
        
        return data
    except Exception as e:
        print(f"API fetch error for {path}: {e}")
        raise


def clear_cache(pattern: str = "*"):
    """Clear cache for specific patterns."""
    # Clear in-memory cache (full clear only)
    if pattern == "*":
        memory_cache.clear()
    
    # Clear Redis with pattern support  
    cleared = redis_cache.clear_pattern(pattern)
    print(f"Cleared {cleared} Redis keys matching '{pattern}'")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    stats = {
        "memory_cache": {
            "size": len(memory_cache),
            "maxsize": memory_cache.maxsize,
            "ttl": memory_cache.ttl
        },
        "redis_available": redis_cache.client is not None
    }
    
    if redis_cache.client:
        try:
            info = redis_cache.client.info()
            stats["redis"] = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except:
            stats["redis"] = {"error": "Could not get Redis stats"}
    
    return stats