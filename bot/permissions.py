from __future__ import annotations

import time

from aiogram.exceptions import TelegramAPIError
from aiogram.types import Chat, Message

from core import redis as _redis
from core.config import settings

_ADMIN_STATUSES = frozenset({"creator", "administrator"})
_RESTRICT_RIGHT = "can_restrict_members"
_fallback_cache: dict[tuple[int, int], tuple[bool, float]] = {}
_fallback_bot_cache: dict[int, tuple[bool, float]] = {}


async def _redis_get_bool(key: str) -> bool | None:
    raw = await _redis.get(key)
    if raw is None:
        return None
    return raw == "1"


async def _redis_set_bool(key: str, value: bool, ttl: int) -> None:
    await _redis.set(key, "1" if value else "0", ttl)


async def is_admin(message: Message) -> bool:
    user = message.from_user
    chat = message.chat
    if user is None:
        return False
    if chat.type == "private":
        return True

    key = f"admin:{chat.id}:{user.id}"
    cached = await _redis_get_bool(key)
    if cached is not None:
        return cached

    fallback_key = (chat.id, user.id)
    now = time.monotonic()
    fallback = _fallback_cache.get(fallback_key)
    if fallback is not None and fallback[1] > now:
        return fallback[0]

    try:
        member = await chat.get_member(user.id)
    except TelegramAPIError:
        return False

    is_admin_now = member.status in _ADMIN_STATUSES
    await _redis_set_bool(key, is_admin_now, int(settings.admin_cache_ttl))
    _fallback_cache[fallback_key] = (is_admin_now, now + settings.admin_cache_ttl)
    return is_admin_now


async def can_restrict(chat: Chat) -> bool:
    key = f"restrict:{chat.id}"
    cached = await _redis_get_bool(key)
    if cached is not None:
        return cached

    now = time.monotonic()
    fallback = _fallback_bot_cache.get(chat.id)
    if fallback is not None and fallback[1] > now:
        return fallback[0]

    try:
        me = await chat.get_member(chat.bot.id)
    except TelegramAPIError:
        return False

    can = me.status == "creator" or (
        me.status == "administrator" and getattr(me, _RESTRICT_RIGHT, False)
    )
    await _redis_set_bool(key, can, int(settings.admin_cache_ttl))
    _fallback_bot_cache[chat.id] = (can, now + settings.admin_cache_ttl)
    return can
