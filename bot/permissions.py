from __future__ import annotations

from contextlib import suppress

from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

_ADMIN_STATUSES = {"creator", "administrator"}


async def is_admin(message: Message) -> bool:
    user = message.from_user
    chat = message.chat
    if user is None:
        return False
    if chat.type == "private":
        return True
    with suppress(TelegramAPIError):
        member = await chat.get_member(user.id)
        return member.status in _ADMIN_STATUSES
    return False
