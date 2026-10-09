import hashlib
import json
import logging
import inspect
from functools import wraps
from typing import Any, Callable, Optional
from cachetools import TTLCache

logger = logging.getLogger(__name__)


memory_cache = TTLCache(maxsize=1000, ttl=3600)

def generate_cache_key(func_name: str, *args, **kwargs) -> str:
    
    try:
        # Sort keys to ensure consistent hashing
        key_data = json.dumps(
            {"func": func_name, "args": args, "kwargs": kwargs}, 
            sort_keys=True, 
            default=str
        )
        return hashlib.md5(key_data.encode()).hexdigest()
    except Exception as e:
        logger.warning(f"Failed to generate cache key: {e}")
        return f"{func_name}_fallback_{time.time()}"

def cached(ttl: int = 3600):
   
    def decorator(func: Callable) -> Callable:
        # Check if function is async
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = generate_cache_key(func.__name__, *args, **kwargs)
            
            # Check Memory Cache
            if key in memory_cache:
                logger.debug(f"cache_hit: {func.__name__}", extra={"key": key})
                return memory_cache[key]
            
            # Execute and store
            result = await func(*args, **kwargs)
            memory_cache[key] = result
            logger.debug(f"cache_miss: {func.__name__}", extra={"key": key})
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = generate_cache_key(func.__name__, *args, **kwargs)
            
            if key in memory_cache:
                logger.debug(f"cache_hit: {func.__name__}", extra={"key": key})
                return memory_cache[key]
            
            result = func(*args, **kwargs)
            memory_cache[key] = result
            logger.debug(f"cache_miss: {func.__name__}", extra={"key": key})
            return result

        return async_wrapper if is_async else sync_wrapper
    
    return decorator

def clear_cache():
    memory_cache.clear()
    logger.info("system_cache_cleared")

def get_cache_stats() -> dict:
   
    return {
        "current_size": len(memory_cache),
        "max_size": memory_cache.maxsize,
        "ttl_seconds": memory_cache.ttl,
        "utilization_pct": round((len(memory_cache) / memory_cache.maxsize) * 100, 2)
    }