from __future__ import annotations

from pydantic import BaseModel, Field


class ThresholdIn(BaseModel):
    threshold: float = Field(ge=0.0, le=1.0)


class DailyPoint(BaseModel):
    day: str
    count: int


class Offender(BaseModel):
    user_id: int
    username: str | None
    count: int


class StatsOut(BaseModel):
    total: int
    by_category: dict[str, int]
    top_offenders: list[Offender]
    daily: list[DailyPoint]


class EventOut(BaseModel):
    id: int
    user_id: int
    username: str | None
    score: float
    category: str
    timestamp: str


class ThresholdOut(BaseModel):
    threshold: float
