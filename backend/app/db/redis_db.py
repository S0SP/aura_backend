"""
AURA Redis Database Connection
Async Redis client for caching and queue management
"""

from typing import Optional, Any, Union
import json
from redis import asyncio as aioredis

from app.core.config import settings
from app.core.logging import logger

# Global Redis client
redis_client: Optional[aioredis.Redis] = None


async def connect_redis() -> None:
    """
    Connect to Redis.
    Creates a global Redis client instance.
    """
    global redis_client
    
    try:
        logger.info(f"Connecting to Redis at {settings.REDIS_URL}...")
        
        redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            db=settings.REDIS_DB,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50
        )
        
        # Verify connection
        await redis_client.ping()
        
        logger.info("✅ Connected to Redis")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        redis_client = None
        raise


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> aioredis.Redis:
    """
    Get the Redis client instance.
    
    Returns:
        Redis client instance
        
    Raises:
        RuntimeError if Redis is not connected
    """
    if redis_client is None:
        raise RuntimeError("Redis is not connected. Call connect_redis() first.")
    return redis_client


# ===========================================
# Cache Operations
# ===========================================

async def cache_set(
    key: str, 
    value: Any, 
    expire_seconds: int = 3600
) -> bool:
    """
    Set a value in cache.
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        expire_seconds: TTL in seconds (default 1 hour)
        
    Returns:
        True if successful
    """
    try:
        client = get_redis()
        serialized = json.dumps(value, default=str)
        await client.setex(key, expire_seconds, serialized)
        return True
    except Exception as e:
        logger.warning(f"Cache set failed for key {key}: {e}")
        return False


async def cache_get(key: str) -> Optional[Any]:
    """
    Get a value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found
    """
    try:
        client = get_redis()
        value = await client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning(f"Cache get failed for key {key}: {e}")
        return None


async def cache_delete(key: str) -> bool:
    """Delete a key from cache."""
    try:
        client = get_redis()
        await client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete failed for key {key}: {e}")
        return False


async def cache_exists(key: str) -> bool:
    """Check if a key exists in cache."""
    try:
        client = get_redis()
        return bool(await client.exists(key))
    except Exception:
        return False


# ===========================================
# Queue Operations (for Celery alternative)
# ===========================================

async def queue_push(queue_name: str, item: dict) -> bool:
    """
    Push an item to a queue.
    
    Args:
        queue_name: Name of the queue
        item: Item to push (will be JSON serialized)
        
    Returns:
        True if successful
    """
    try:
        client = get_redis()
        serialized = json.dumps(item, default=str)
        await client.rpush(queue_name, serialized)
        return True
    except Exception as e:
        logger.error(f"Queue push failed for {queue_name}: {e}")
        return False


async def queue_pop(queue_name: str, timeout: int = 0) -> Optional[dict]:
    """
    Pop an item from a queue (blocking).
    
    Args:
        queue_name: Name of the queue
        timeout: Timeout in seconds (0 = non-blocking)
        
    Returns:
        Popped item or None
    """
    try:
        client = get_redis()
        if timeout > 0:
            result = await client.blpop(queue_name, timeout=timeout)
            if result:
                return json.loads(result[1])
        else:
            value = await client.lpop(queue_name)
            if value:
                return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Queue pop failed for {queue_name}: {e}")
        return None


async def queue_length(queue_name: str) -> int:
    """Get the length of a queue."""
    try:
        client = get_redis()
        return await client.llen(queue_name)
    except Exception:
        return 0


# ===========================================
# Pub/Sub Operations (for WebSocket)
# ===========================================

async def publish(channel: str, message: dict) -> int:
    """
    Publish a message to a channel.
    
    Args:
        channel: Channel name
        message: Message to publish
        
    Returns:
        Number of subscribers that received the message
    """
    try:
        client = get_redis()
        serialized = json.dumps(message, default=str)
        return await client.publish(channel, serialized)
    except Exception as e:
        logger.error(f"Publish failed for channel {channel}: {e}")
        return 0


async def subscribe(channel: str):
    """
    Subscribe to a channel.
    
    Args:
        channel: Channel name
        
    Returns:
        Pubsub object
    """
    client = get_redis()
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    return pubsub


# ===========================================
# Rate Limiting
# ===========================================

async def rate_limit_check(
    identifier: str, 
    max_requests: int, 
    window_seconds: int
) -> bool:
    """
    Check rate limit using sliding window.
    
    Args:
        identifier: Unique identifier (e.g., user_id, IP)
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        
    Returns:
        True if request is allowed, False if rate limited
    """
    try:
        client = get_redis()
        key = f"ratelimit:{identifier}"
        
        # Increment counter
        current = await client.incr(key)
        
        # Set expiry on first request
        if current == 1:
            await client.expire(key, window_seconds)
        
        return current <= max_requests
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        return True  # Allow on error


# ===========================================
# Session Storage
# ===========================================

async def store_session(
    session_id: str, 
    data: dict, 
    expire_seconds: int = 86400
) -> bool:
    """Store session data."""
    return await cache_set(f"session:{session_id}", data, expire_seconds)


async def get_session(session_id: str) -> Optional[dict]:
    """Get session data."""
    return await cache_get(f"session:{session_id}")


async def delete_session(session_id: str) -> bool:
    """Delete session data."""
    return await cache_delete(f"session:{session_id}")


# ===========================================
# Verification Status Tracking
# ===========================================

async def set_verification_status(
    verification_id: str, 
    status: dict
) -> bool:
    """
    Set verification status for real-time tracking.
    
    Args:
        verification_id: Verification ID
        status: Status data
        
    Returns:
        True if successful
    """
    key = f"verification:{verification_id}:status"
    return await cache_set(key, status, expire_seconds=3600)


async def get_verification_status(verification_id: str) -> Optional[dict]:
    """Get verification status."""
    key = f"verification:{verification_id}:status"
    return await cache_get(key)


# Queue names
class Queues:
    """Redis queue names."""
    VERIFICATION = "queue:verification"
    DEBATE = "queue:debate"
    NOTIFICATION = "queue:notification"
    AUDIO_GENERATION = "queue:audio"
