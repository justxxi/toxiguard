from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    event,
    func,
    select,
    update,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DB_URL = os.environ.get("DB_URL", "sqlite+aiosqlite:///toxiguard.db")
DEFAULT_THRESHOLD = 0.75


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_chat_time", "chat_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class Warning_(Base):
    __tablename__ = "warnings"
    __table_args__ = (Index("ix_warnings_chat_user", "chat_id", "user_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    count: Mapped[int] = mapped_column(Integer, default=0)
    banned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ChatSettings(Base):
    __tablename__ = "chat_settings"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    threshold: Mapped[float] = mapped_column(Float, default=DEFAULT_THRESHOLD)


engine = create_async_engine(DB_URL, echo=False, pool_pre_ping=True)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)

_threshold_cache: dict[int, float] = {}


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, _) -> None:
    if "sqlite" not in str(dbapi_connection.__class__).lower() and "sqlite" not in DB_URL:
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA temp_store=MEMORY")
    finally:
        cursor.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_threshold(chat_id: int, default: float = DEFAULT_THRESHOLD) -> float:
    cached = _threshold_cache.get(chat_id)
    if cached is not None:
        return cached
    async with SessionLocal() as s:
        row = await s.get(ChatSettings, chat_id)
    value = row.threshold if row is not None else default
    _threshold_cache[chat_id] = value
    return value


async def set_threshold(chat_id: int, threshold: float) -> float:
    threshold = max(0.0, min(1.0, threshold))
    stmt = (
        sqlite_insert(ChatSettings)
        .values(chat_id=chat_id, threshold=threshold)
        .on_conflict_do_update(
            index_elements=[ChatSettings.chat_id],
            set_={"threshold": threshold},
        )
    )
    async with SessionLocal() as s:
        await s.execute(stmt)
        await s.commit()
    _threshold_cache[chat_id] = threshold
    return threshold


async def record_incident(
    chat_id: int,
    user_id: int,
    username: str | None,
    score: float,
    category: str,
) -> int:
    async with SessionLocal() as s:
        s.add(
            Event(
                chat_id=chat_id,
                user_id=user_id,
                username=username,
                score=score,
                category=category,
            )
        )

        upsert = (
            sqlite_insert(Warning_)
            .values(chat_id=chat_id, user_id=user_id, count=1)
            .on_conflict_do_update(
                index_elements=["chat_id", "user_id"],
                set_={"count": Warning_.__table__.c.count + 1},
            )
        )
        await s.execute(upsert)
        count = (
            await s.execute(
                select(Warning_.count).where(
                    Warning_.chat_id == chat_id, Warning_.user_id == user_id
                )
            )
        ).scalar_one()
        await s.commit()
        return count


async def add_warning(chat_id: int, user_id: int) -> int:
    upsert = (
        sqlite_insert(Warning_)
        .values(chat_id=chat_id, user_id=user_id, count=1)
        .on_conflict_do_update(
            index_elements=["chat_id", "user_id"],
            set_={"count": Warning_.__table__.c.count + 1},
        )
    )
    async with SessionLocal() as s:
        await s.execute(upsert)
        count = (
            await s.execute(
                select(Warning_.count).where(
                    Warning_.chat_id == chat_id, Warning_.user_id == user_id
                )
            )
        ).scalar_one()
        await s.commit()
        return count


async def remove_warning(chat_id: int, user_id: int) -> int:
    async with SessionLocal() as s:
        await s.execute(
            update(Warning_)
            .where(
                Warning_.chat_id == chat_id,
                Warning_.user_id == user_id,
                Warning_.count > 0,
            )
            .values(count=Warning_.count - 1)
        )
        count = (
            await s.execute(
                select(Warning_.count).where(
                    Warning_.chat_id == chat_id, Warning_.user_id == user_id
                )
            )
        ).scalar_one_or_none() or 0
        await s.commit()
        return count


async def reset_warnings(chat_id: int, user_id: int) -> None:
    async with SessionLocal() as s:
        await s.execute(
            update(Warning_)
            .where(Warning_.chat_id == chat_id, Warning_.user_id == user_id)
            .values(count=0, banned_at=None)
        )
        await s.commit()


async def mark_banned(chat_id: int, user_id: int) -> None:
    async with SessionLocal() as s:
        await s.execute(
            update(Warning_)
            .where(Warning_.chat_id == chat_id, Warning_.user_id == user_id)
            .values(banned_at=_now(), count=0)
        )
        await s.commit()


async def get_stats(chat_id: int | None = None) -> dict:
    async with SessionLocal() as s:
        q_total = select(func.count(Event.id))
        q_cat = select(Event.category, func.count(Event.id)).group_by(Event.category)
        q_top = (
            select(Event.user_id, Event.username, func.count(Event.id).label("n"))
            .group_by(Event.user_id, Event.username)
            .order_by(func.count(Event.id).desc())
            .limit(10)
        )
        if chat_id is not None:
            q_total = q_total.where(Event.chat_id == chat_id)
            q_cat = q_cat.where(Event.chat_id == chat_id)
            q_top = q_top.where(Event.chat_id == chat_id)

        total = (await s.execute(q_total)).scalar_one()
        by_category = dict((await s.execute(q_cat)).all())
        offenders = [
            {"user_id": uid, "username": name, "count": n}
            for uid, name, n in (await s.execute(q_top)).all()
        ]

        return {"total": total, "by_category": by_category, "top_offenders": offenders}


async def get_events(chat_id: int | None = None, limit: int = 50) -> list[dict]:
    async with SessionLocal() as s:
        q = select(Event).order_by(Event.timestamp.desc()).limit(limit)
        if chat_id is not None:
            q = q.where(Event.chat_id == chat_id)
        rows = (await s.execute(q)).scalars().all()
        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "username": r.username,
                "score": r.score,
                "category": r.category,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ]


async def get_daily(chat_id: int | None = None, days: int = 14) -> list[dict]:
    async with SessionLocal() as s:
        day = func.date(Event.timestamp).label("day")
        q = select(day, func.count(Event.id)).group_by(day).order_by(day.desc()).limit(days)
        if chat_id is not None:
            q = q.where(Event.chat_id == chat_id)
        rows = (await s.execute(q)).all()
        return list(reversed([{"day": str(d), "count": n} for d, n in rows]))
