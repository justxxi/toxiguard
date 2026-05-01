from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatPermissions, Message, User

from bot.permissions import is_admin
from bot.profanity import is_profane
from core.analyzer import analyze
from core.database import get_threshold, mark_banned, record_incident

log = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.75
MUTE_AFTER = 3
MUTE_DURATION = timedelta(hours=1)
MUTED_PERMS = ChatPermissions(can_send_messages=False)


def _mention(user: User | None) -> str:
    if user is None:
        return "друг"
    return f"@{user.username}" if user.username else (user.full_name or "друг")


class ToxicityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not self._should_check(event):
            return await handler(event, data)

        if await is_admin(event):
            return await handler(event, data)

        text = event.text or event.caption or ""
        profane = is_profane(text)

        if profane:
            score = 1.0
            category = "profanity"
        else:
            scores = await analyze(text)
            score = max(scores.values())
            threshold = await get_threshold(event.chat.id, DEFAULT_THRESHOLD)
            data["toxicity"] = scores
            if score < threshold:
                return await handler(event, data)
            category = "toxicity"

        await self._strike(event, score, category, profane)
        return await handler(event, data)

    @staticmethod
    def _should_check(event: Message) -> bool:
        if event.from_user is None or event.from_user.is_bot:
            return False
        text = event.text or event.caption
        if not text or text.startswith("/"):
            return False
        return True

    @staticmethod
    async def _strike(event: Message, score: float, category: str, profane: bool) -> None:
        with suppress(TelegramAPIError):
            await event.delete()

        user = event.from_user
        if user is None:
            return

        count = await record_incident(
            chat_id=event.chat.id,
            user_id=user.id,
            username=user.username or user.full_name,
            score=score,
            category=category,
        )

        mention = _mention(user)
        tail = "ругаемся помягче" if profane else f"токсично — {score:.0%}"
        body = f"⚠️ {mention}, {tail} · {count}/{MUTE_AFTER}"

        with suppress(TelegramAPIError):
            await event.answer(body)

        if count >= MUTE_AFTER:
            until = datetime.now(UTC) + MUTE_DURATION
            try:
                await event.chat.restrict(user.id, permissions=MUTED_PERMS, until_date=until)
            except TelegramAPIError as exc:
                log.warning("restrict failed for %s: %s", user.id, exc)
                return
            await mark_banned(event.chat.id, user.id)
            with suppress(TelegramAPIError):
                await event.answer(f"🤐 {mention} — час тишины")
