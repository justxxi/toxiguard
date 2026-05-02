from __future__ import annotations

import json
import logging
from typing import Any

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore[assignment]

from core.config import settings

log = logging.getLogger(__name__)

_client: Any | None = None
_username_cache: dict[str, int] = {}


async def _client() -> Any | None:
    global _client
    if _client is not None:
        return _client
    if redis is None:
        return None
    try:
        _client = redis.from_url(
            getattr(settings, "redis_url", "redis://localhost:6379"),
            decode_responses=True,
        )
        await _client.ping()
        log.info("redis connected")
        return _client
    except Exception:
        _client = None
        return None


async def get(key: str) -> str | None:
    c = await _client()
    if c is None:
        return None
    try:
        return await c.get(key)
    except Exception:
        return None


async def set(key: str, value: str, ttl: int) -> None:
    c = await _client()
    if c is None:
        return
    try:
        await c.setex(key, ttl, value)
    except Exception:
        pass


async def delete(key: str) -> None:
    c = await _client()
    if c is None:
        return
    try:
        await c.delete(key)
    except Exception:
        pass


async def incr(key: str, ttl: int) -> int:
    c = await _client()
    if c is None:
        return 0
    try:
        pipe = c.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = await pipe.execute()
        return int(results[0])
    except Exception:
        return 0


async def get_json(key: str) -> Any | None:
    raw = await get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


async def set_json(key: str, value: Any, ttl: int) -> None:
    try:
        await set(key, json.dumps(value), ttl)
    except Exception:
        pass


async def set_username(username: str, user_id: int, ttl: int = 604800) -> None:
    key = f"u:{username.lstrip('@').strip().lower()}"
    _username_cache[key] = user_id
    await set(key, str(user_id), ttl)


async def resolve_username(username: str) -> int | None:
    key = f"u:{username.lstrip('@').strip().lower()}"
    raw = await get(key)
    if raw is not None:
        try:
            return int(raw)
        except ValueError:
            pass
    return _username_cache.get(key)
