from __future__ import annotations

import hashlib

import pytest

from core import analyzer


@pytest.fixture(autouse=True)
def _clear_cache(monkeypatch):
    analyzer._cache.clear()
    yield
    analyzer._cache.clear()


def _mock_predict(text: str) -> analyzer.Scores:
    if "kill" in text.lower():
        return {"toxicity": 0.9, "insult": 0.1, "threat": 0.8, "obscene": 0.0, "identity_hate": 0.0}
    return {"toxicity": 0.1, "insult": 0.0, "threat": 0.0, "obscene": 0.0, "identity_hate": 0.0}


@pytest.fixture
def mock_model(monkeypatch):
    monkeypatch.setattr(analyzer, "_predict", _mock_predict)


@pytest.mark.asyncio
async def test_short_text_skipped() -> None:
    scores = await analyzer.analyze("hi")
    assert scores == analyzer._ZERO


@pytest.mark.asyncio
async def test_caches_repeated_text(mock_model) -> None:
    text = "we should kill the build"
    a = await analyzer.analyze(text)
    assert a["toxicity"] > 0.5
    key = hashlib.sha256(text.lower().encode()).hexdigest()
    assert key in analyzer._cache

    b = await analyzer.analyze(text)
    assert a == b


@pytest.mark.asyncio
async def test_cache_evicts_lru(monkeypatch, mock_model) -> None:
    monkeypatch.setattr(analyzer, "settings", type(analyzer.settings)(cache_size=2))
    await analyzer.analyze("первое сообщение")
    await analyzer.analyze("второе сообщение")
    await analyzer.analyze("третье сообщение")
    assert len(analyzer._cache) <= 2
