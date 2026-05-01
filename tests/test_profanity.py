from __future__ import annotations

import pytest

from bot.profanity import is_profane


@pytest.mark.parametrize(
    "text",
    [
        "ты что блять делаешь",
        "сука как же надоело",
        "fuck this",
        "you bitch",
        "пошёл нахуй",
    ],
)
def test_detects_profanity(text: str) -> None:
    assert is_profane(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "доброе утро",
        "hello world",
        "класс получился",
        "сосуд для цветов",
    ],
)
def test_clean_text_passes(text: str) -> None:
    assert is_profane(text) is False
