"""
Tests for Caching Module
"""

import pytest
import time
from utils.cache import InMemoryCache, CacheManager, cached


class TestInMemoryCache:
    """Tests for in-memory cache."""
    
    def test_cache_set_get(self):
        """Test basic cache operations."""
        cache = InMemoryCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None
    
    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = InMemoryCache(ttl_seconds=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        time.sleep(1.1)  # Wait for TTL
        assert cache.get("key1") is None
    
    def test_cache_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = InMemoryCache(max_size=2)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_cache_delete(self):
        """Test cache deletion."""
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['size'] == 1


class TestCacheManager:
    """Tests for cache manager."""
    
    def test_cache_manager_init(self):
        """Test cache manager initialization."""
        manager = CacheManager(use_redis=False)
        assert manager is not None
        assert not manager.use_redis
    
    def test_cache_manager_operations(self):
        """Test cache manager basic operations."""
        manager = CacheManager(use_redis=False)
        manager.set("test_key", {"data": "value"})
        result = manager.get("test_key")
        assert result == {"data": "value"}
    
    def test_cache_manager_stats(self):
        """Test getting cache statistics."""
        manager = CacheManager(use_redis=False)
        stats = manager.get_stats()
        assert 'type' in stats
        assert stats['type'] == 'in_memory'


class TestCachedDecorator:
    """Tests for cached decorator."""
    
    def test_cached_decorator(self):
        """Test cached decorator functionality."""
        call_count = 0
        
        @cached(ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call - should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call with same args - should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented
        
        # Different args - should execute function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

