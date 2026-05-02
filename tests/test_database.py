from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from core import database as db
from core.config import settings


@pytest_asyncio.fixture
async def fresh_db():
    db._threshold_cache.clear()
    await db.init_db()
    yield
    async with db.engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_add_warning_increments(fresh_db) -> None:
    assert await db.add_warning(1, 100) == 1
    assert await db.add_warning(1, 100) == 2
    assert await db.add_warning(1, 100) == 3


@pytest.mark.asyncio
async def test_remove_and_reset(fresh_db) -> None:
    await db.add_warning(1, 100)
    await db.add_warning(1, 100)
    assert await db.remove_warning(1, 100) == 1
    await db.reset_warnings(1, 100)
    assert await db.remove_warning(1, 100) == 0


@pytest.mark.asyncio
async def test_record_incident_logs_and_warns(fresh_db) -> None:
    count = await db.record_incident(
        chat_id=1, user_id=100, username="alice", score=0.9, category="toxicity"
    )
    assert count == 1
    stats = await db.get_stats(1)
    assert stats["total"] == 1
    assert stats["by_category"] == {"toxicity": 1}
    assert stats["top_offenders"][0]["username"] == "alice"


@pytest.mark.asyncio
async def test_threshold_persists_and_caches(fresh_db) -> None:
    assert await db.get_threshold(42) == pytest.approx(settings.default_threshold)
    await db.set_threshold(42, 0.6)
    assert await db.get_threshold(42) == pytest.approx(0.6)
    assert db._threshold_cache[42] == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_threshold_clamped(fresh_db) -> None:
    assert await db.set_threshold(1, 1.5) == 1.0
    assert await db.set_threshold(1, -0.2) == 0.0


@pytest.mark.asyncio
async def test_mark_banned_resets_count(fresh_db) -> None:
    for _ in range(3):
        await db.add_warning(1, 100)
    await db.mark_banned(1, 100)
    assert await db.add_warning(1, 100) == 1


@pytest.mark.asyncio
async def test_cleanup_events(fresh_db) -> None:
    old = datetime.now(UTC) - timedelta(days=settings.event_retention_days + 1)
    async with db.SessionLocal() as s:
        s.add(
            db.Event(
                chat_id=1, user_id=1, username="x", score=0.5, category="toxicity", timestamp=old
            )
        )
        await s.commit()
    removed = await db.cleanup_events()
    assert removed == 1
    stats = await db.get_stats(1)
    assert stats["total"] == 0
