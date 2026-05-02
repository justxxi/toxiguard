from __future__ import annotations

from aiogram.types import User


def mention(user: User | None) -> str:
    if user is None:
        return "друг"
    return f"@{user.username}" if user.username else (user.full_name or "друг")
