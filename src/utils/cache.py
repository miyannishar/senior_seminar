"""
Caching Layer for RAG System
Implements in-memory and Redis-based caching for improved performance.
"""

import hashlib
import json
import time
from typing import Any, Optional, Dict
from functools import wraps
from datetime import datetime, timedelta

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Try to import Redis (optional dependency)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️  Redis not installed. Using in-memory cache only.")


class InMemoryCache:
    """Simple in-memory LRU cache."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize in-memory cache.
        
        Args:
            max_size: Maximum number of entries
            ttl_seconds: Time-to-live for cache entries
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        self.hits = 0
        self.misses = 0
        
        logger.info(f"✅ InMemoryCache initialized (max_size={max_size}, ttl={ttl_seconds}s)")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self.access_times:
            return True
        return time.time() - self.access_times[key] > self.ttl_seconds
    
    def _evict_oldest(self):
        """Evict oldest entry when cache is full."""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times, key=self.access_times.get)
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
        logger.debug(f"🗑️  Evicted oldest cache entry: {oldest_key}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self.cache and not self._is_expired(key):
            self.hits += 1
            self.access_times[key] = time.time()
            logger.debug(f"✅ Cache hit: {key}")
            return self.cache[key]['value']
        
        self.misses += 1
        logger.debug(f"❌ Cache miss: {key}")
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache."""
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
        self.access_times[key] = time.time()
        logger.debug(f"💾 Cache set: {key}")
    
    def delete(self, key: str):
        """Delete entry from cache."""
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            logger.debug(f"🗑️  Cache deleted: {key}")
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.access_times.clear()
        self.hits = 0
        self.misses = 0
        logger.info("🧹 Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'type': 'in_memory',
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate_percent': round(hit_rate, 2),
            'ttl_seconds': self.ttl_seconds
        }


class RedisCache:
    """Redis-based cache for distributed systems."""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        ttl_seconds: int = 3600,
        prefix: str = 'rag:'
    ):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            ttl_seconds: Time-to-live for cache entries
            prefix: Key prefix for namespacing
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not installed. Install with: pip install redis")
        
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_connect_timeout=2
        )
        self.ttl_seconds = ttl_seconds
        self.prefix = prefix
        
        # Test connection
        try:
            self.client.ping()
            logger.info(f"✅ Redis cache initialized at {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        try:
            full_key = self._make_key(key)
            value = self.client.get(full_key)
            
            if value:
                logger.debug(f"✅ Redis cache hit: {key}")
                return json.loads(value)
            
            logger.debug(f"❌ Redis cache miss: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any):
        """Set value in Redis."""
        try:
            full_key = self._make_key(key)
            serialized = json.dumps(value, default=str)
            self.client.setex(full_key, self.ttl_seconds, serialized)
            logger.debug(f"💾 Redis cache set: {key}")
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete(self, key: str):
        """Delete entry from Redis."""
        try:
            full_key = self._make_key(key)
            self.client.delete(full_key)
            logger.debug(f"🗑️  Redis cache deleted: {key}")
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    
    def clear(self):
        """Clear all cache entries with our prefix."""
        try:
            pattern = f"{self.prefix}*"
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
            logger.info(f"🧹 Redis cache cleared ({len(keys)} keys)")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            info = self.client.info('stats')
            pattern = f"{self.prefix}*"
            our_keys = len(self.client.keys(pattern))
            
            return {
                'type': 'redis',
                'keys_count': our_keys,
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'ttl_seconds': self.ttl_seconds
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {'type': 'redis', 'error': str(e)}


class CacheManager:
    """
    Unified cache manager supporting multiple backends.
    """
    
    def __init__(
        self,
        use_redis: bool = False,
        redis_url: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize cache manager.
        
        Args:
            use_redis: Whether to use Redis (if available)
            redis_url: Redis connection URL
            **kwargs: Additional arguments for cache initialization
        """
        self.use_redis = use_redis and REDIS_AVAILABLE
        
        if self.use_redis:
            try:
                if redis_url:
                    # Parse redis URL
                    # Format: redis://host:port/db
                    parts = redis_url.replace('redis://', '').split('/')
                    host_port = parts[0].split(':')
                    host = host_port[0]
                    port = int(host_port[1]) if len(host_port) > 1 else 6379
                    db = int(parts[1]) if len(parts) > 1 else 0
                    
                    self.cache = RedisCache(host=host, port=port, db=db, **kwargs)
                else:
                    self.cache = RedisCache(**kwargs)
                    
                logger.info("🚀 Using Redis cache")
            except Exception as e:
                logger.warning(f"⚠️  Redis initialization failed: {e}. Falling back to in-memory cache.")
                self.cache = InMemoryCache(**kwargs)
                self.use_redis = False
        else:
            self.cache = InMemoryCache(**kwargs)
            logger.info("📦 Using in-memory cache")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self.cache.get(key)
    
    def set(self, key: str, value: Any):
        """Set value in cache."""
        self.cache.set(key, value)
    
    def delete(self, key: str):
        """Delete entry from cache."""
        self.cache.delete(key)
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()


def cached(ttl: int = 3600):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live for cache entry in seconds
    """
    def decorator(func):
        cache_manager = CacheManager(ttl_seconds=ttl)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = {
                'func': func.__name__,
                'args': str(args),
                'kwargs': str(sorted(kwargs.items()))
            }
            cache_key = hashlib.md5(
                json.dumps(key_data, sort_keys=True).encode()
            ).hexdigest()
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result)
            
            return result
        
        # Attach cache manager for testing/debugging
        wrapper.cache = cache_manager
        return wrapper
    
    return decorator


# Global cache instance
_global_cache: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache

