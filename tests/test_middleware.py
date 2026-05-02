from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.middleware import ToxicityMiddleware
from core.config import settings


@pytest.fixture
def make_message():
    def _inner(text: str = "hello", is_bot: bool = False, chat_type: str = "supergroup"):
        msg = MagicMock()
        msg.from_user = MagicMock()
        msg.from_user.is_bot = is_bot
        msg.from_user.id = 42
        msg.from_user.username = "user"
        msg.from_user.full_name = "User"
        msg.chat = MagicMock()
        msg.chat.id = 1
        msg.chat.type = chat_type
        msg.text = text
        msg.caption = None
        msg.delete = AsyncMock()
        msg.answer = AsyncMock()
        return msg

    return _inner


@pytest.mark.asyncio
async def test_skips_commands(make_message) -> None:
    mw = ToxicityMiddleware()
    handler = AsyncMock(return_value="ok")
    msg = make_message(text="/start")
    result = await mw(handler, msg, {})
    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_skips_bots(make_message) -> None:
    mw = ToxicityMiddleware()
    handler = AsyncMock(return_value="ok")
    msg = make_message(is_bot=True)
    result = await mw(handler, msg, {})
    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.middleware.is_admin", new_callable=AsyncMock, return_value=True)
async def test_skips_admins(_, make_message) -> None:
    mw = ToxicityMiddleware()
    handler = AsyncMock(return_value="ok")
    msg = make_message(text="some text")
    result = await mw(handler, msg, {})
    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.middleware.is_admin", new_callable=AsyncMock, return_value=False)
@patch("bot.middleware.is_profane", return_value=True)
@patch("bot.middleware.can_restrict", new_callable=AsyncMock, return_value=True)
@patch("bot.middleware.record_incident", new_callable=AsyncMock, return_value=settings.mute_after)
@patch("bot.middleware.mark_banned", new_callable=AsyncMock)
async def test_strike_on_profanity(_, __, ___, ____, _____, make_message) -> None:
    mw = ToxicityMiddleware()
    handler = AsyncMock(return_value="ok")
    msg = make_message(text="bad word")
    msg.chat.restrict = AsyncMock()
    result = await mw(handler, msg, {})
    assert result == "ok"
    msg.delete.assert_awaited_once()
    msg.answer.assert_awaited()
