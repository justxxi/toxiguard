from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DB_URL = "sqlite+aiosqlite:///toxiguard.db"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    score: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class Warning_(Base):
    __tablename__ = "warnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ChatSettings(Base):
    __tablename__ = "chat_settings"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    threshold: Mapped[float] = mapped_column(Float, default=0.75)


engine = create_async_engine(DB_URL, echo=False)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _find_warning(s: AsyncSession, chat_id: int, user_id: int) -> Optional[Warning_]:
    return (
        await s.execute(
            select(Warning_).where(Warning_.chat_id == chat_id, Warning_.user_id == user_id)
        )
    ).scalar_one_or_none()


async def add_event(
    chat_id: int,
    user_id: int,
    username: Optional[str],
    score: float,
    category: str,
) -> None:
    async with SessionLocal() as s:
        s.add(Event(chat_id=chat_id, user_id=user_id, username=username, score=score, category=category))
        await s.commit()


async def add_warning(chat_id: int, user_id: int) -> int:
    async with SessionLocal() as s:
        row = await _find_warning(s, chat_id, user_id)
        if row is None:
            row = Warning_(chat_id=chat_id, user_id=user_id, count=1)
            s.add(row)
        else:
            row.count += 1
        await s.commit()
        return row.count


async def remove_warning(chat_id: int, user_id: int) -> int:
    async with SessionLocal() as s:
        row = await _find_warning(s, chat_id, user_id)
        if row is None or row.count == 0:
            return 0
        row.count -= 1
        if row.count == 0:
            row.banned_at = None
        await s.commit()
        return row.count


async def get_warnings(chat_id: int, user_id: int) -> int:
    async with SessionLocal() as s:
        row = (
            await s.execute(
                select(Warning_.count).where(
                    Warning_.chat_id == chat_id, Warning_.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        return row or 0


async def mark_banned(chat_id: int, user_id: int) -> None:
    async with SessionLocal() as s:
        row = await _find_warning(s, chat_id, user_id)
        if row is not None:
            row.banned_at = _now()
            await s.commit()


async def get_stats(chat_id: Optional[int] = None) -> dict:
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


async def get_events(chat_id: Optional[int] = None, limit: int = 50) -> list[dict]:
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


async def get_daily(chat_id: Optional[int] = None, days: int = 14) -> list[dict]:
    async with SessionLocal() as s:
        day = func.date(Event.timestamp).label("day")
        q = select(day, func.count(Event.id)).group_by(day).order_by(day.desc()).limit(days)
        if chat_id is not None:
            q = q.where(Event.chat_id == chat_id)
        rows = (await s.execute(q)).all()
        return list(reversed([{"day": str(d), "count": n} for d, n in rows]))


async def set_threshold(chat_id: int, threshold: float) -> float:
    threshold = max(0.0, min(1.0, threshold))
    async with SessionLocal() as s:
        row = await s.get(ChatSettings, chat_id)
        if row is None:
            s.add(ChatSettings(chat_id=chat_id, threshold=threshold))
        else:
            row.threshold = threshold
        await s.commit()
        return threshold


async def log_incident(chat_id: int, user_id: int, text: str, score: float) -> None:
    await add_event(chat_id=chat_id, user_id=user_id, username=None, score=score, category="toxicity")
