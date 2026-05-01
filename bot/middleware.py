from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatPermissions, Message

from bot.profanity import is_profane
from core.analyzer import analyze
from core.database import add_warning, get_threshold, log_incident

DEFAULT_THRESHOLD = 0.75
MUTE_AFTER = 3
MUTE_DURATION = timedelta(hours=1)
MUTED_PERMS = ChatPermissions(can_send_messages=False)

Handler = Callable[[Message, dict[str, Any]], Awaitable[Any]]


def _mention(user) -> str:
    if user is None:
        return "друг"
    if user.username:
        return f"@{user.username}"
    return user.full_name or "друг"


class ToxicityMiddleware(BaseMiddleware):
    async def __call__(self, handler: Handler, event: Message, data: dict[str, Any]) -> Any:
        if not event.text or event.text.startswith("/"):
            return await handler(event, data)

        text = event.text
        scores = await analyze(text)
        ai_score = max(scores.values())
        threshold = await get_threshold(event.chat.id, DEFAULT_THRESHOLD)
        profane = is_profane(text)

        data["toxicity"] = scores

        if not profane and ai_score < threshold:
            return await handler(event, data)

        score = max(ai_score, 1.0 if profane else 0.0)
        user = event.from_user
        await log_incident(
            chat_id=event.chat.id,
            user_id=user.id if user else 0,
            text=text,
            score=score,
            username=(user.username or user.full_name) if user else None,
            category="profanity" if profane else "toxicity",
        )
        await self._enforce(event, score, profane)

        return await handler(event, data)

    @staticmethod
    async def _enforce(event: Message, score: float, profane: bool) -> None:
        with suppress(TelegramAPIError):
            await event.delete()

        user = event.from_user
        if user is None:
            return

        count = await add_warning(event.chat.id, user.id)
        mention = _mention(user)

        if profane:
            tail = "не выражайся в этом чате."
        else:
            tail = f"токсичность {score:.0%} — давай мягче."

        text = f"{mention}, {tail} ({count}/{MUTE_AFTER})"

        with suppress(TelegramAPIError):
            await event.answer(text)

        if count >= MUTE_AFTER:
            until = datetime.now(timezone.utc) + MUTE_DURATION
            with suppress(TelegramAPIError):
                await event.chat.restrict(user.id, permissions=MUTED_PERMS, until_date=until)
            with suppress(TelegramAPIError):
                await event.answer(f"{mention} в тишине на час — остынет и вернётся")
