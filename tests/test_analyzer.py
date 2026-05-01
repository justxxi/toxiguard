from __future__ import annotations

import pytest

from core import analyzer


@pytest.fixture(autouse=True)
def _clear_cache():
    analyzer._cache.clear()
    yield
    analyzer._cache.clear()


@pytest.mark.asyncio
async def test_short_text_skipped() -> None:
    scores = await analyzer.analyze("hi")
    assert scores == analyzer._ZERO


@pytest.mark.asyncio
async def test_caches_repeated_text() -> None:
    a = await analyzer.analyze("we should kill the build")
    assert a["toxicity"] > 0.5
    assert "we should kill the build".lower()[:512] in analyzer._cache

    b = await analyzer.analyze("we should kill the build")
    assert a == b


@pytest.mark.asyncio
async def test_cache_evicts_lru(monkeypatch) -> None:
    monkeypatch.setattr(analyzer, "CACHE_SIZE", 2)
    await analyzer.analyze("первое сообщение")
    await analyzer.analyze("второе сообщение")
    await analyzer.analyze("третье сообщение")
    assert len(analyzer._cache) <= 2
