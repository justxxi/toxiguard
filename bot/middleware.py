#middleware
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from core.analyzer import analyze
from core.database import log_incident

log = logging.getLogger(__name__)

WARN_THRESHOLD = 0.6
BAN_THRESHOLD = 0.9

class ToxicityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not event.text:
            return await handler(event, data)

        scores = await analyze(event.text)
        score = max(scores.values())
        data["toxicity"] = scores

        if score >= WARN_THRESHOLD:
            await log_incident(
                chat_id=event.chat.id,
                user_id=event.from_user.id if event.from_user else 0,
                text=event.text,
                score=score,
            )
            await self._enforce(event, score)

        return await handler(event, data)

    @staticmethod
    async def _enforce(event: Message, score: float) -> None:
        if score >= BAN_THRESHOLD:
            try:
                await event.delete()
            except Exception as exc:
                log.warning("delete failed: %s", exc)
            return

        await event.reply(
            f"⚠️ замечена токсичность ({score:.0%}). прошу, тише тон."
        )
