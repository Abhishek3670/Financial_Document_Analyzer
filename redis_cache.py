"""
Redis Caching Layer
Provides caching functionality for expensive operations like LLM calls and database queries
"""
import redis
import json
import hashlib
import logging
from typing import Any, Optional, Dict, Union
from datetime import datetime, timedelta
import os
from functools import wraps
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisCache:
    """Redis caching manager"""
    
    def __init__(self):
        self.enabled = os.getenv("REDIS_CACHE_ENABLED", "true").lower() == "true"
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.default_ttl = int(os.getenv("REDIS_DEFAULT_TTL", "3600"))  # 1 hour
        self.client = None
        self._connect()
        
    def _connect(self):
        """Connect to Redis"""
        if not self.enabled:
            logger.info("Redis caching disabled")
            return
            
        try:
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # Keep binary for pickle
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"✅ Connected to Redis: {self.redis_url}")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            logger.warning("Continuing without caching...")
            self.enabled = False
            self.client = None
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from function arguments"""
        # Create a string representation of args and kwargs
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())  # Sort for consistent ordering
        }
        
        # Create hash of the serialized data
        key_string = json.dumps(key_data, default=str, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"cache:{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.client:
            return None
            
        try:
            value = self.client.get(key)
            if value is not None:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Redis GET error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        if not self.enabled or not self.client:
            return False
            
        try:
            ttl = ttl or self.default_ttl
            serialized_value = pickle.dumps(value)
            result = self.client.setex(key, ttl, serialized_value)
            return bool(result)
        except Exception as e:
            logger.warning(f"Redis SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled or not self.client:
            return False
            
        try:
            result = self.client.delete(key)
            return bool(result)
        except Exception as e:
            logger.warning(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled or not self.client:
            return False
            
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.warning(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.enabled or not self.client:
            return 0
            
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis FLUSH error for pattern {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled or not self.client:
            return {"enabled": False, "message": "Redis not available"}
            
        try:
            info = self.client.info()
            return {
                "enabled": True,
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "cache_hit_ratio": self._calculate_hit_ratio(info)
            }
        except Exception as e:
            logger.warning(f"Redis INFO error: {e}")
            return {"enabled": True, "connected": False, "error": str(e)}
    
    def _calculate_hit_ratio(self, info: Dict) -> float:
        """Calculate cache hit ratio"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

# Global cache instance
redis_cache = RedisCache()

def cache_result(prefix: str = "default", ttl: Optional[int] = None, 
                invalidate_on_error: bool = True):
    """
    Decorator to cache function results
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        invalidate_on_error: Whether to invalidate cache on function error
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = redis_cache._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache first
            cached_result = redis_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for {func.__name__}")
                return cached_result
            
            logger.debug(f"Cache MISS for {func.__name__}")
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache the result
                redis_cache.set(cache_key, result, ttl)
                
                return result
                
            except Exception as e:
                # Optionally invalidate cache on error
                if invalidate_on_error:
                    redis_cache.delete(cache_key)
                raise
                
        return wrapper
    return decorator

def cache_llm_result(model: str = "default", ttl: int = 7200):
    """
    Specialized decorator for caching LLM results (2 hours default)
    """
    return cache_result(prefix=f"llm:{model}", ttl=ttl)

def cache_analysis_result(ttl: int = 86400):
    """
    Specialized decorator for caching analysis results (24 hours default)
    """
    return cache_result(prefix="analysis", ttl=ttl)

def cache_database_query(table: str = "default", ttl: int = 1800):
    """
    Specialized decorator for caching database queries (30 minutes default)
    """
    return cache_result(prefix=f"db:{table}", ttl=ttl)

# Cache invalidation helpers
def invalidate_user_cache(user_id: str):
    """Invalidate all cache entries for a user"""
    pattern = f"cache:*user:{user_id}*"
    count = redis_cache.flush_pattern(pattern)
    logger.info(f"Invalidated {count} cache entries for user {user_id}")

def invalidate_analysis_cache():
    """Invalidate all analysis cache entries"""
    pattern = "cache:analysis:*"
    count = redis_cache.flush_pattern(pattern)
    logger.info(f"Invalidated {count} analysis cache entries")

def invalidate_llm_cache(model: str = None):
    """Invalidate LLM cache entries"""
    if model:
        pattern = f"cache:llm:{model}:*"
    else:
        pattern = "cache:llm:*"
    count = redis_cache.flush_pattern(pattern)
    logger.info(f"Invalidated {count} LLM cache entries")

# Example usage functions for testing
@cache_llm_result(model="gpt-3.5-turbo", ttl=3600)
def example_llm_call(prompt: str, model: str = "gpt-3.5-turbo"):
    """Example LLM call with caching"""
    # This would be replaced with actual LLM call
    import time
    time.sleep(0.1)  # Simulate API call
    return f"Response to: {prompt[:50]}... (model: {model})"

@cache_analysis_result(ttl=7200)
def example_document_analysis(document_content: str, analysis_type: str):
    """Example document analysis with caching"""
    # This would be replaced with actual analysis
    import time
    time.sleep(0.5)  # Simulate processing
    return {
        "analysis_type": analysis_type,
        "content_length": len(document_content),
        "summary": f"Analysis of {len(document_content)} characters",
        "timestamp": datetime.now().isoformat()
    }

@cache_database_query(table="users", ttl=900)
def example_user_query(user_id: str):
    """Example database query with caching"""
    # This would be replaced with actual DB query
    return {
        "user_id": user_id,
        "cached_at": datetime.now().isoformat(),
        "data": f"User data for {user_id}"
    }
