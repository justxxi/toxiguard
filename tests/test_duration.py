from __future__ import annotations

from datetime import timedelta

import pytest

from bot.handlers import _parse_duration


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("30s", timedelta(seconds=30)),
        ("15m", timedelta(minutes=15)),
        ("2h", timedelta(hours=2)),
        ("1d", timedelta(days=1)),
        ("  3H  ", timedelta(hours=3)),
    ],
)
def test_parses_valid_durations(raw: str, expected: timedelta) -> None:
    assert _parse_duration(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "0h", "-1m", "5", "1y", "h1"])
def test_rejects_invalid_durations(raw: str) -> None:
    assert _parse_duration(raw) is None
