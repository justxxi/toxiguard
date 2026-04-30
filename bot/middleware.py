from __future__ import annotations

from contextlib import suppress
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from core.analyzer import analyze
from core.database import log_incident

WARN_THRESHOLD = 0.6
BAN_THRESHOLD = 0.9

Handler = Callable[[Message, dict[str, Any]], Awaitable[Any]]


class ToxicityMiddleware(BaseMiddleware):
    async def __call__(self, handler: Handler, event: Message, data: dict[str, Any]) -> Any:
        if not event.text:
            return await handler(event, data)

        scores = await analyze(event.text)
        score = max(scores.values())
        data["toxicity"] = scores

        if score >= WARN_THRESHOLD:
            user = event.from_user
            await log_incident(
                chat_id=event.chat.id,
                user_id=user.id if user else 0,
                text=event.text,
                score=score,
                username=(user.username or user.full_name) if user else None,
            )
            await self._enforce(event, score)

        return await handler(event, data)

    @staticmethod
    async def _enforce(event: Message, score: float) -> None:
        if score >= BAN_THRESHOLD:
            with suppress(TelegramAPIError):
                await event.delete()
            return

        with suppress(TelegramAPIError):
            await event.reply(f"⚠️ замечена токсичность ({score:.0%}). прошу, тише тон.")
