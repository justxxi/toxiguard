from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.filters import CommandObject

from bot.handlers import _parse_duration


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("30m", 1800),
        ("2h", 7200),
        ("1d", 86400),
        ("100s", 100),
    ],
)
def test_parse_duration_valid(raw, expected) -> None:
    result = _parse_duration(raw)
    assert result is not None
    assert result.total_seconds() == expected


def test_parse_duration_invalid() -> None:
    assert _parse_duration("abc") is None
    assert _parse_duration("-1h") is None
    assert _parse_duration("999d") is None


@pytest.mark.asyncio
@patch("bot.handlers.is_admin", new_callable=AsyncMock, return_value=False)
async def test_stats_requires_admin(_) -> None:
    from bot.handlers import cmd_stats

    msg = MagicMock()
    msg.reply = AsyncMock()
    msg.chat = MagicMock()
    await cmd_stats(msg)
    msg.reply.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.is_admin", new_callable=AsyncMock, return_value=True)
@patch(
    "bot.handlers.get_stats",
    new_callable=AsyncMock,
    return_value={"total": 5, "by_category": {}, "top_offenders": []},
)
@patch("bot.handlers.get_threshold", new_callable=AsyncMock, return_value=0.75)
async def test_stats_replies(_, __, ___) -> None:
    from bot.handlers import cmd_stats

    msg = MagicMock()
    msg.chat = MagicMock()
    msg.chat.id = 1
    msg.answer = AsyncMock()
    await cmd_stats(msg)
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.is_admin", new_callable=AsyncMock, return_value=True)
@patch("bot.handlers.can_restrict", new_callable=AsyncMock, return_value=True)
@patch("bot.handlers.set_threshold", new_callable=AsyncMock, return_value=0.6)
async def test_threshold_sets(_, __, ___) -> None:
    from bot.handlers import cmd_threshold

    msg = MagicMock()
    msg.chat = MagicMock()
    msg.chat.id = 1
    msg.answer = AsyncMock()
    cmd = CommandObject(command="threshold", args="0.6")
    await cmd_threshold(msg, cmd)
    msg.answer.assert_awaited_once()
