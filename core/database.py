#database
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Integer,
    String,
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DB_URL = "sqlite+aiosqlite:///toxiguard.db"

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
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

class Warning_(Base):
    __tablename__ = "warnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

engine = create_async_engine(DB_URL, echo=False)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def add_event(
    chat_id: int,
    user_id: int,
    username: Optional[str],
    score: float,
    category: str,
) -> None:
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
        await s.commit()

async def add_warning(chat_id: int, user_id: int) -> int:
    async with SessionLocal() as s:
        row = (
            await s.execute(
                select(Warning_).where(
                    Warning_.chat_id == chat_id, Warning_.user_id == user_id
                )
            )
        ).scalar_one_or_none()

        if row is None:
            row = Warning_(chat_id=chat_id, user_id=user_id, count=1)
            s.add(row)
        else:
            row.count += 1

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
        row = (
            await s.execute(
                select(Warning_).where(
                    Warning_.chat_id == chat_id, Warning_.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            row.banned_at = datetime.utcnow()
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

        return {
            "total": total,
            "by_category": by_category,
            "top_offenders": offenders,
        }

async def log_incident(
    chat_id: int, user_id: int, text: str, score: float
) -> None:
    await add_event(
        chat_id=chat_id,
        user_id=user_id,
        username=None,
        score=score,
        category="toxicity",
    )
