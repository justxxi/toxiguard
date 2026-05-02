from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import ChatPermissions, Message

from bot.permissions import can_restrict, is_admin
from bot.profanity import is_profane
from bot.utils import mention
from core import redis as _redis
from core.analyzer import analyze
from core.config import settings
from core.database import get_threshold, mark_banned, record_incident
from core.metrics import messages_processed, telegram_api_errors, toxicity_detected

log = logging.getLogger(__name__)

MUTED_PERMS = ChatPermissions(can_send_messages=False)


class ToxicityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user and user.username:
            await _redis.set_username(user.username, user.id)

        if not self._should_check(event):
            return await handler(event, data)

        messages_processed.labels(chat_id=event.chat.id).inc()

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
            threshold = await get_threshold(event.chat.id)
            if score < threshold:
                return await handler(event, data)
            category = "toxicity"

        toxicity_detected.labels(category=category, chat_id=event.chat.id).inc()
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

        m = mention(user)
        tail = "ругаемся помягче" if profane else f"токсично — {score:.0%}"
        body = f"⚠️ {m}, {tail} · {count}/{settings.mute_after}"

        with suppress(TelegramAPIError):
            await event.answer(body)

        if count >= settings.mute_after:
            if not await can_restrict(event.chat):
                return
            until = datetime.now(UTC) + settings.mute_duration
            try:
                await event.chat.restrict(user.id, permissions=MUTED_PERMS, until_date=until)
            except TelegramRetryAfter as exc:
                log.warning("flood wait for %s: %ss", user.id, exc.retry_after)
                telegram_api_errors.labels(method="restrict").inc()
                return
            except TelegramAPIError as exc:
                log.warning("restrict failed for %s: %s", user.id, exc)
                telegram_api_errors.labels(method="restrict").inc()
                return
            await mark_banned(event.chat.id, user.id)
            with suppress(TelegramAPIError):
                await event.answer(f"🤐 {m} — час тишины")
