from __future__ import annotations

import time

from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

_ADMIN_STATUSES = frozenset({"creator", "administrator"})
_TTL = 60.0
_cache: dict[tuple[int, int], tuple[bool, float]] = {}


async def is_admin(message: Message) -> bool:
    user = message.from_user
    chat = message.chat
    if user is None:
        return False
    if chat.type == "private":
        return True

    key = (chat.id, user.id)
    now = time.monotonic()
    cached = _cache.get(key)
    if cached is not None and cached[1] > now:
        return cached[0]

    try:
        member = await chat.get_member(user.id)
    except TelegramAPIError:
        return False

    is_admin_now = member.status in _ADMIN_STATUSES
    _cache[key] = (is_admin_now, now + _TTL)
    return is_admin_now
